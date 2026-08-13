/*
 * PATAP v0.5 descriptor-level capture prototype.
 *
 * This program is intentionally an evaluator-side recorder: its JSONL output
 * may contain privileged pid/fd/device/inode information.  The public adapter
 * is a separate program and must discard those fields.  A snapshot is made
 * while the traced task is stopped at the successful open/mmap boundary; a
 * descriptor whose access mode permits writes is never presented as a stable
 * input observation.
 *
 * Supported at this stage: x86-64 Linux open/openat/creat, read/pread64,
 * write/pwrite64, close, dup family, fork/vfork/clone, exec and exit.  Events
 * outside that set are explicitly emitted as unresolved, not silently treated
 * as artifact-instance provenance.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <linux/ptrace.h>
#include <signal.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ptrace.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/user.h>
#include <sys/wait.h>
#include <unistd.h>

#ifndef __x86_64__
#error "ptrace_recorder currently supports x86-64 Linux only"
#endif

#define MAX_TASKS 4096
#define MAX_FDS 4096
struct fd_state { bool known, writable, dirty, snapshot; dev_t dev; ino_t ino; char hash[17]; };
struct task { pid_t pid; bool syscall_entry; long syscall_no; unsigned long args[6]; unsigned epoch; struct fd_state fd[MAX_FDS]; };
static struct task tasks[MAX_TASKS]; static FILE *out; static unsigned long seq;

static struct task *find_task(pid_t pid, bool create) {
  for (int i=0;i<MAX_TASKS;i++) if (tasks[i].pid==pid) return &tasks[i];
  if (!create) return NULL;
  for (int i=0;i<MAX_TASKS;i++) if (!tasks[i].pid) { tasks[i].pid=pid; tasks[i].epoch=1; return &tasks[i]; }
  return NULL;
}
static void emit(const char *kind, pid_t pid, unsigned epoch, int fd, const struct fd_state *s, const char *detail) {
  fprintf(out,"{\"seq\":%lu,\"kind\":\"%s\",\"pid\":%d,\"epoch\":%u,\"fd\":%d",++seq,kind,pid,epoch,fd);
  if (s && s->known) fprintf(out,",\"dev\":%ju,\"inode\":%ju,\"hash\":\"%s\"",(uintmax_t)s->dev,(uintmax_t)s->ino,s->hash);
  if (detail) fprintf(out,",\"detail\":\"%s\"",detail);
  fputs("}\n",out); fflush(out);
}
static uint64_t fnv_fd(pid_t pid,int fd) {
  char p[64]; snprintf(p,sizeof p,"/proc/%d/fd/%d",pid,fd); int d=open(p,O_RDONLY|O_CLOEXEC); if(d<0)return 0;
  uint64_t h=1469598103934665603ULL; unsigned char b[8192]; ssize_t n;
  while((n=read(d,b,sizeof b))>0) for(ssize_t i=0;i<n;i++){h^=b[i];h*=1099511628211ULL;}
  close(d); return n<0?0:h;
}
static bool snapshot(pid_t pid,int fd, bool writable, struct fd_state *s) {
  char p[64]; struct stat st; snprintf(p,sizeof p,"/proc/%d/fd/%d",pid,fd);
  if (stat(p,&st) || !S_ISREG(st.st_mode)) return false;
  s->known=true;s->writable=writable;s->dirty=false;s->snapshot=false;s->dev=st.st_dev;s->ino=st.st_ino;
  if (writable) { strcpy(s->hash,"UNRESOLVED"); return true; }
  uint64_t h=fnv_fd(pid,fd); if(!h){strcpy(s->hash,"UNRESOLVED");return true;}
  snprintf(s->hash,sizeof s->hash,"%016" PRIx64,h);s->snapshot=true;return true;
}
static void copy_task(struct task *from,pid_t child) { struct task *to=find_task(child,true); if(to) { memcpy(to->fd,from->fd,sizeof to->fd);to->epoch=from->epoch;to->syscall_entry=false; } }
static void enter_syscall(struct task *t, struct user_regs_struct *r) { t->syscall_no=r->orig_rax;t->args[0]=r->rdi;t->args[1]=r->rsi;t->args[2]=r->rdx;t->args[3]=r->r10;t->args[4]=r->r8;t->args[5]=r->r9;t->syscall_entry=true; }
static void exit_syscall(struct task *t, struct user_regs_struct *r) {
  long ret=(long)r->rax, no=t->syscall_no; t->syscall_entry=false; if(ret<0)return;
  if (no==2 || no==257 || no==85) { /* open, openat, creat */
    int fd=(int)ret; unsigned long flags=no==257?t->args[2]:(no==2?t->args[1]:O_WRONLY|O_CREAT|O_TRUNC);
    if(fd>=0&&fd<MAX_FDS) { bool w=(flags&O_WRONLY)||(flags&O_RDWR); if(snapshot(t->pid,fd,w,&t->fd[fd])) emit(w?"open_write_unresolved":"read_snapshot",t->pid,t->epoch,fd,&t->fd[fd],NULL); else emit("nonregular_open",t->pid,t->epoch,fd,NULL,NULL); }
  } else if (no==0 || no==17) { /* read/pread64 */ int fd=(int)t->args[0]; if(fd>=0&&fd<MAX_FDS&&t->fd[fd].known) emit(t->fd[fd].snapshot?"read_version":"read_unresolved",t->pid,t->epoch,fd,&t->fd[fd],NULL);
  } else if (no==1 || no==18) { int fd=(int)t->args[0]; if(fd>=0&&fd<MAX_FDS&&t->fd[fd].known){t->fd[fd].dirty=true;emit("write",t->pid,t->epoch,fd,&t->fd[fd],NULL);}
  } else if (no==3) { int fd=(int)t->args[0];if(fd>=0&&fd<MAX_FDS&&t->fd[fd].known){if(t->fd[fd].dirty){uint64_t h=fnv_fd(t->pid,fd);if(h)snprintf(t->fd[fd].hash,sizeof t->fd[fd].hash,"%016" PRIx64,h);else strcpy(t->fd[fd].hash,"UNRESOLVED");emit("publish_close",t->pid,t->epoch,fd,&t->fd[fd],NULL);}memset(&t->fd[fd],0,sizeof t->fd[fd]);}
  } else if (no==32 || no==33 || no==292) { int old=(int)t->args[0], fd=(int)ret;if(old>=0&&old<MAX_FDS&&fd>=0&&fd<MAX_FDS){t->fd[fd]=t->fd[old];emit("dup",t->pid,t->epoch,fd,&t->fd[fd],NULL);}
  } else if (no==9) { emit("mmap_unresolved",t->pid,t->epoch,(int)t->args[4],NULL,"mmap requires explicit mapping-lifetime audit"); }
}
int main(int argc,char **argv) {
  if(argc<4||strcmp(argv[1],"--output")||strcmp(argv[3],"--")){fprintf(stderr,"usage: %s --output EVENTS.jsonl -- command...\n",argv[0]);return 2;}
  out=fopen(argv[2],"w");if(!out){perror("output");return 2;} pid_t child=fork();if(child<0){perror("fork");return 2;}
  if(!child){ptrace(PTRACE_TRACEME,0,0,0);raise(SIGSTOP);execvp(argv[4],argv+4);_exit(127);} int status;waitpid(child,&status,0);
  long options=PTRACE_O_TRACESYSGOOD|PTRACE_O_TRACEFORK|PTRACE_O_TRACEVFORK|PTRACE_O_TRACECLONE|PTRACE_O_TRACEEXEC|PTRACE_O_TRACEEXIT;
  ptrace(PTRACE_SETOPTIONS,child,0,options);find_task(child,true);ptrace(PTRACE_SYSCALL,child,0,0);
  while(1){pid_t pid=waitpid(-1,&status,__WALL);if(pid<0){if(errno==ECHILD)break;continue;}struct task*t=find_task(pid,true); if(WIFEXITED(status)||WIFSIGNALED(status)){emit("exit",pid,t->epoch,-1,NULL,NULL);t->pid=0;continue;}if(!WIFSTOPPED(status))continue;int sig=WSTOPSIG(status),event=status>>16;
    if(sig==(SIGTRAP|0x80)){struct user_regs_struct r;ptrace(PTRACE_GETREGS,pid,0,&r);if(!t->syscall_entry)enter_syscall(t,&r);else exit_syscall(t,&r);ptrace(PTRACE_SYSCALL,pid,0,0);continue;}
    if(sig==SIGTRAP&&event){unsigned long message=0;ptrace(PTRACE_GETEVENTMSG,pid,0,&message);if(event==PTRACE_EVENT_FORK||event==PTRACE_EVENT_VFORK||event==PTRACE_EVENT_CLONE)copy_task(t,(pid_t)message);if(event==PTRACE_EVENT_EXEC){t->epoch++;emit("exec",pid,t->epoch,-1,NULL,NULL);}ptrace(PTRACE_SYSCALL,pid,0,0);continue;}
    ptrace(PTRACE_SYSCALL,pid,0,(void *)(long)(sig==SIGSTOP?0:sig));
  } fclose(out);return 0;
}
