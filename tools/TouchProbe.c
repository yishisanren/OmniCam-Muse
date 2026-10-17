/* Bounded real touchscreen gesture for this phone; never changes input settings. */
#include <linux/input.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <errno.h>

static int fd = -1;
static int active;
static void event(unsigned short type, unsigned short code, int value) {
    struct input_event e = {0};
    e.type = type; e.code = code; e.value = value;
    if (write(fd, &e, sizeof e) != sizeof e) { perror("touch write"); exit(2); }
}
static void release(void) {
    if (!active || fd < 0) return;
    active = 0;
    /* Best effort releases also run after a failed write. */
    struct input_event e[5] = {0};
    e[0].type=EV_ABS; e[0].code=ABS_MT_SLOT;
    e[1].type=EV_ABS; e[1].code=ABS_MT_TRACKING_ID; e[1].value=-1;
    e[2].type=EV_KEY; e[2].code=BTN_TOUCH;
    e[3].type=EV_KEY; e[3].code=BTN_TOOL_FINGER;
    e[4].type=EV_SYN; e[4].code=SYN_REPORT;
    (void)write(fd,e,sizeof e);
}
static void interrupted(int signal_number) { release(); _exit(128+signal_number); }
static int parse(const char *s) {
    char *end; errno=0; long v=strtol(s,&end,10);
    if(errno || *end || v<0 || v>10000) { fputs("Invalid integer\n",stderr); exit(2); }
    return (int)v;
}
int main(int argc, char **argv) {
    if(argc!=6) { fputs("x1 y1 x2 y2 duration_ms\n",stderr); return 2; }
    int x1=parse(argv[1]), y1=parse(argv[2]), x2=parse(argv[3]), y2=parse(argv[4]), duration=parse(argv[5]);
    if(x1>1215 || x2>1215 || y1>2639 || y2>2639 || duration<100 || duration>1000) return 2;
    fd=open("/dev/input/event2",O_RDWR|O_CLOEXEC);
    if(fd<0) { perror("touch open"); return 2; }
    char name[80]={0}; struct input_absinfo x={0},y={0};
    if(ioctl(fd,EVIOCGNAME(sizeof name),name)<0 || strcmp(name,"touchpanel") ||
       ioctl(fd,EVIOCGABS(ABS_MT_POSITION_X),&x)<0 || x.maximum!=19455 ||
       ioctl(fd,EVIOCGABS(ABS_MT_POSITION_Y),&y)<0 || y.maximum!=42239) return 2;
    int slots[11]={ABS_MT_TRACKING_ID};
    if(ioctl(fd,EVIOCGMTSLOTS(sizeof slots),slots)<0) return 2;
    for(int i=1;i<11;i++) if(slots[i]>=0) { fputs("Physical touch active; abort\n",stderr); return 2; }
    atexit(release); signal(SIGINT,interrupted); signal(SIGTERM,interrupted); signal(SIGALRM,interrupted); alarm(3);
    active=1;
    event(EV_ABS,ABS_MT_SLOT,0);
    event(EV_ABS,ABS_MT_TRACKING_ID,7816);
    event(EV_KEY,BTN_TOUCH,1); event(EV_KEY,BTN_TOOL_FINGER,1);
    event(EV_ABS,ABS_MT_TOUCH_MAJOR,10); event(EV_ABS,ABS_MT_TOUCH_MINOR,8);
    event(EV_ABS,ABS_MT_POSITION_X,x1*16+8); event(EV_ABS,ABS_MT_POSITION_Y,y1*16+8);
    event(EV_SYN,SYN_REPORT,0);
    int steps=duration/20;
    for(int i=1;i<=steps;i++) {
        usleep((useconds_t)(duration/steps)*1000);
        event(EV_ABS,ABS_MT_POSITION_X,(x1+(x2-x1)*i/steps)*16+8);
        event(EV_ABS,ABS_MT_POSITION_Y,(y1+(y2-y1)*i/steps)*16+8);
        event(EV_SYN,SYN_REPORT,0);
    }
    release(); alarm(0); close(fd); fd=-1;
    puts("Touch gesture completed and released");
    return 0;
}
