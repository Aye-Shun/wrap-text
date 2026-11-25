#include <stdbool.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>

#define MAX_WIDTH 240U

struct reflow {
    unsigned width;
    unsigned column;
    unsigned used;
    unsigned char prefix[MAX_WIDTH + 1U];
    bool word;
    bool streaming;
    bool output;
    bool paragraph_break;
    bool line_has_text;
};

static bool put_byte(int c) {
    return fputc(c, stdout) != EOF;
}

static bool begin_word(struct reflow *state, unsigned length) {
    if (state->paragraph_break && state->output) {
        if (!put_byte('\n') || !put_byte('\n')) return false;
        state->column = 0U;
    } else if (state->column != 0U) {
        if (state->column + 1U + length > state->width) {
            if (!put_byte('\n')) return false;
            state->column = 0U;
        } else {
            if (!put_byte(' ')) return false;
            ++state->column;
        }
    }
    state->column += length;
    state->output = true;
    state->paragraph_break = false;
    return true;
}

static bool finish_word(struct reflow *state) {
    if (!state->word) return true;
    if (!state->streaming) {
        if (!begin_word(state, state->used)) return false;
        if (fwrite(state->prefix, 1U, state->used, stdout) != state->used) return false;
    }
    state->word = false;
    state->streaming = false;
    state->used = 0U;
    return true;
}

static bool add_letter(struct reflow *state, int c) {
    state->line_has_text = true;
    state->word = true;
    if (state->streaming) return put_byte(c);
    state->prefix[state->used++] = (unsigned char)c;
    if (state->used > state->width) {
        if (!begin_word(state, state->used)) return false;
        if (fwrite(state->prefix, 1U, state->used, stdout) != state->used) return false;
        state->used = 0U;
        state->streaming = true;
    }
    return true;
}

static bool end_line(struct reflow *state) {
    if (!finish_word(state)) return false;
    if (!state->line_has_text && state->output) state->paragraph_break = true;
    state->line_has_text = false;
    return true;
}

static bool parse_width(const char *text, unsigned *width) {
    unsigned value = 0U;
    if (*text == '\0') return false;
    for (const unsigned char *p = (const unsigned char *)text; *p != '\0'; ++p) {
        if (*p < '0' || *p > '9') return false;
        const unsigned digit = (unsigned)(*p - '0');
        if (value > (MAX_WIDTH - digit) / 10U) return false;
        value = value * 10U + digit;
    }
    if (value == 0U) return false;
    *width = value;
    return true;
}

static int usage_error(void) {
    fputs("wrap-text: usage: wrap-text [--width 1..240] [FILE|-]\n", stderr);
    return 2;
}

int main(int argc, char **argv) {
#ifdef SIGPIPE
    (void)signal(SIGPIPE, SIG_IGN);
#endif
    if (argc == 2 && strcmp(argv[1], "--help") == 0) {
        if (puts("Usage: wrap-text [--width 1..240] [FILE|-]\n"
                 "Reflow ASCII paragraphs to standard output (default width: 72).\n"
                 "Blank lines separate paragraphs; overlong words stay whole.\n"
                 "Use -- before a filename beginning with '-'.") == EOF || fflush(stdout) == EOF) {
            fputs("wrap-text: output error\n", stderr);
            return 1;
        }
        return 0;
    }
    struct reflow state = {.width = 72U};
    const char *path = NULL;
    bool width_seen = false;
    bool options = true;
    for (int i = 1; i < argc; ++i) {
        if (options && strcmp(argv[i], "--") == 0) {
            options = false;
        } else if (options && strcmp(argv[i], "--width") == 0) {
            if (width_seen || i + 1 >= argc || !parse_width(argv[++i], &state.width)) return usage_error();
            width_seen = true;
        } else {
            if (path != NULL || (options && argv[i][0] == '-' && strcmp(argv[i], "-") != 0)) return usage_error();
            path = argv[i];
        }
    }
    FILE *input = stdin;
    if (path != NULL && strcmp(path, "-") != 0) {
        input = fopen(path, "rb");
        if (input == NULL) {
            fprintf(stderr, "wrap-text: cannot open input: %s\n", path);
            return 1;
        }
    }
    bool swallow_lf = false;
    bool output_ok = true;
    bool valid = true;
    int c;
    while ((c = fgetc(input)) != EOF) {
        if (swallow_lf) {
            swallow_lf = false;
            if (c == '\n') continue;
        }
        if (c == '\r' || c == '\n') {
            output_ok = end_line(&state);
            swallow_lf = c == '\r';
        } else if (c == ' ' || c == '\t' || c == '\v' || c == '\f') {
            output_ok = finish_word(&state);
        } else if (c >= 33 && c <= 126) {
            output_ok = add_letter(&state, c);
        } else {
            fputs("wrap-text: input must be ASCII text without control bytes\n", stderr);
            valid = false;
            break;
        }
        if (!output_ok) break;
    }
    const bool read_ok = ferror(input) == 0;
    bool close_ok = true;
    if (input != stdin) close_ok = fclose(input) == 0;
    if (!read_ok || !close_ok) fputs("wrap-text: input read error\n", stderr);
    if (valid && read_ok && close_ok && output_ok) {
        output_ok = finish_word(&state);
        if (output_ok && state.output) output_ok = put_byte('\n');
    }
    if (fflush(stdout) == EOF || ferror(stdout) != 0) output_ok = false;
    if (!output_ok) fputs("wrap-text: output error\n", stderr);
    return valid && read_ok && close_ok && output_ok ? 0 : 1;
}
