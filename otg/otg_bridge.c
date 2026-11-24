// Bridge each "Twin USB Joystick" (0810:0001) PS1/PS2 adapter to its own
// standard Android gamepad using uinput, so PES sees separate P1/P2 pads.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <poll.h>
#include <linux/input.h>
#include <linux/uinput.h>

#define MAX_PADS 4
#define MAX_SOURCES 8

typedef struct {
    int ufd;
    int source_fd;
    char path[64];
    char name[64];
} Pad;

static Pad g_pads[MAX_PADS];
static int g_pad_count = 0;
static int g_pad_of_source[MAX_SOURCES];

static void emit_to(int idx, int type, int code, int val) {
    if (idx < 0 || idx >= g_pad_count) return;
    int fd = g_pads[idx].ufd;
    if (fd < 0) return;

    struct input_event e;
    memset(&e, 0, sizeof(e));
    e.type = type;
    e.code = code;
    e.value = val;
    if (write(fd, &e, sizeof(e)) != (ssize_t)sizeof(e)) perror("write uinput");
}

static int create_pad(int idx) {
    int fd = open("/dev/uinput", O_WRONLY | O_NONBLOCK);
    if (fd < 0) { perror("open /dev/uinput"); return -1; }

    ioctl(fd, UI_SET_EVBIT, EV_KEY);
    ioctl(fd, UI_SET_EVBIT, EV_ABS);

    int keys[] = { BTN_A, BTN_B, BTN_X, BTN_Y, BTN_TL, BTN_TR,
                   BTN_TL2, BTN_TR2, BTN_SELECT, BTN_START,
                   BTN_MODE, BTN_THUMBL, BTN_THUMBR };
    for (unsigned i = 0; i < sizeof(keys)/sizeof(keys[0]); i++)
        ioctl(fd, UI_SET_KEYBIT, keys[i]);

    int axes[] = { ABS_X, ABS_Y, ABS_Z, ABS_RZ, ABS_HAT0X, ABS_HAT0Y };
    for (unsigned i = 0; i < sizeof(axes)/sizeof(axes[0]); i++)
        ioctl(fd, UI_SET_ABSBIT, axes[i]);

    struct uinput_abs_setup a;
    for (unsigned i = 0; i < sizeof(axes)/sizeof(axes[0]); i++) {
        memset(&a, 0, sizeof(a));
        a.code = axes[i];
        if (axes[i] == ABS_HAT0X || axes[i] == ABS_HAT0Y) {
            a.absinfo.minimum = -1; a.absinfo.maximum = 1;
        } else {
            a.absinfo.minimum = -32768; a.absinfo.maximum = 32767;
            a.absinfo.flat = 2048;
        }
        ioctl(fd, UI_ABS_SETUP, &a);
    }

    char name[64];
    char phys[32];
    snprintf(name, sizeof(name), "PES Tuned Gamepad P%d", idx + 1);
    snprintf(phys, sizeof(phys), "pes-otg-p%d", idx + 1);
    ioctl(fd, UI_SET_PHYS, phys);

    struct uinput_setup us;
    memset(&us, 0, sizeof(us));
    us.id.bustype = BUS_USB;
    us.id.vendor  = 0x045e;   // Xbox 360 identity -> Android loads its keylayout
    us.id.product = 0x028e;
    us.id.version = 0x0110;
    strncpy(us.name, name, sizeof(us.name) - 1);

    if (ioctl(fd, UI_DEV_SETUP, &us) < 0) { perror("UI_DEV_SETUP"); close(fd); return -1; }
    if (ioctl(fd, UI_DEV_CREATE) < 0) { perror("UI_DEV_CREATE"); close(fd); return -1; }

    g_pads[idx].ufd = fd;
    strncpy(g_pads[idx].name, name, sizeof(g_pads[idx].name) - 1);
    fprintf(stderr, "created %s\n", name);
    return 0;
}

static void destroy_pads(void) {
    for (int i = 0; i < g_pad_count; i++) {
        if (g_pads[i].ufd >= 0) {
            ioctl(g_pads[i].ufd, UI_DEV_DESTROY);
            close(g_pads[i].ufd);
            g_pads[i].ufd = -1;
        }
        g_pads[i].source_fd = -1;
    }
    g_pad_count = 0;
}

// Map raw HID button code -> standard gamepad button.
static int map_key(int code) {
    switch (code) {
        case BTN_JOYSTICK: return BTN_Y;       // Triangle
        case BTN_THUMB:    return BTN_B;       // Circle
        case BTN_THUMB2:   return BTN_A;       // Cross
        case BTN_TOP:      return BTN_X;       // Square
        case BTN_TOP2:     return BTN_TL2;     // L2
        case BTN_PINKIE:   return BTN_TR2;     // R2
        case BTN_BASE:     return BTN_TL;      // L1
        case BTN_BASE2:    return BTN_TR;      // R1
        case BTN_BASE3:    return BTN_SELECT;
        case BTN_BASE4:    return BTN_START;
        case BTN_BASE5:    return BTN_THUMBL;
        case BTN_BASE6:    return BTN_THUMBR;
        default: return 0;
    }
}

static int map_abs(int code) {
    switch (code) {
        case ABS_X: return ABS_X;
        case ABS_Y: return ABS_Y;
        case ABS_Z: return ABS_Z;
        case ABS_RZ: return ABS_RZ;
        case ABS_HAT0X: return ABS_HAT0X;
        case ABS_HAT0Y: return ABS_HAT0Y;
        default: return -1;
    }
}

static int scale_axis(int code, int val) {
    if (code == ABS_HAT0X || code == ABS_HAT0Y) return val;
    return ((val - 128) * 32767) / 127;
}

static int scan_sources(struct pollfd *pfds, int max) {
    int found = 0;
    for (int i = 0; i < 32 && found < max && g_pad_count < MAX_PADS; i++) {
        char path[64];
        snprintf(path, sizeof(path), "/dev/input/event%d", i);
        int fd = open(path, O_RDONLY);
        if (fd < 0) continue;

        struct input_id id;
        char name[128] = "";
        int have_id = ioctl(fd, EVIOCGID, &id) == 0;
        ioctl(fd, EVIOCGNAME(sizeof(name)), name);

        int target = strstr(name, "Twin USB Joystick") != NULL;
        if (have_id && id.vendor == 0x0810 && id.product == 0x0001) target = 1;
        if (!target) { close(fd); continue; }

        if (ioctl(fd, EVIOCGRAB, 1) < 0) {
            fprintf(stderr, "EVIOCGRAB %s failed: %s\n", path, strerror(errno));
            close(fd);
            continue;
        }

        int pad_idx = g_pad_count;
        if (create_pad(pad_idx) < 0) {
            ioctl(fd, EVIOCGRAB, 0);
            close(fd);
            continue;
        }

        strncpy(g_pads[pad_idx].path, path, sizeof(g_pads[pad_idx].path) - 1);
        g_pads[pad_idx].source_fd = fd;
        pfds[found].fd = fd;
        pfds[found].events = POLLIN;
        pfds[found].revents = 0;
        g_pad_of_source[found] = pad_idx;
        found++;
        g_pad_count++;

        fprintf(stderr, "%s <- %s (%s)\n", g_pads[pad_idx].name, path, name);
    }
    return found;
}

static void close_sources(struct pollfd *pfds, int n) {
    for (int i = 0; i < n; i++) close(pfds[i].fd);
}

static void wait_for_sources(struct pollfd *pfds, int max, int *n) {
    int waiting_logged = 0;
    while (!*n) {
        *n = scan_sources(pfds, max);
        if (!*n) {
            if (!waiting_logged) {
                fprintf(stderr, "waiting for Twin USB Joystick (0810:0001)...\n");
                waiting_logged = 1;
            }
            sleep(2);
        }
    }
}

int main(void) {
    struct pollfd pfds[MAX_SOURCES];
    int n = 0;

    wait_for_sources(pfds, MAX_SOURCES, &n);

    for (;;) {
        int r = poll(pfds, n, -1);
        if (r < 0) { if (errno == EINTR) continue; perror("poll"); break; }

        int dead = 0;
        for (int i = 0; i < n; i++) {
            if (pfds[i].revents & (POLLHUP | POLLERR | POLLNVAL)) { dead = 1; break; }

            if (!(pfds[i].revents & POLLIN)) continue;
            struct input_event ev;
            ssize_t got = read(pfds[i].fd, &ev, sizeof(ev));
            if (got != (ssize_t)sizeof(ev)) { dead = 1; break; }

            int pad_idx = g_pad_of_source[i];
            if (ev.type == EV_KEY) {
                int k = map_key(ev.code);
                if (k) {
                    emit_to(pad_idx, EV_KEY, k, ev.value);
                    emit_to(pad_idx, EV_SYN, SYN_REPORT, 0);
                }
            } else if (ev.type == EV_ABS) {
                int a = map_abs(ev.code);
                if (a >= 0) {
                    emit_to(pad_idx, EV_ABS, a, scale_axis(ev.code, ev.value));
                    emit_to(pad_idx, EV_SYN, SYN_REPORT, 0);
                }
            }
        }
        if (!dead) continue;

        close_sources(pfds, n);
        destroy_pads();
        n = 0;
        fprintf(stderr, "source disconnected, rescanning...\n");
        wait_for_sources(pfds, MAX_SOURCES, &n);
    }

    close_sources(pfds, n);
    destroy_pads();
    return 0;
}
