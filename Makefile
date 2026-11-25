CC = cc
CFLAGS = -std=c17 -O2 -Wall -Wextra -Wpedantic -Wconversion -Wshadow -Werror

.PHONY: all test sanitize clean
all: build/wrap-text

build/wrap-text: src/main.c
	mkdir -p build
	$(CC) $(CPPFLAGS) $(CFLAGS) src/main.c $(LDFLAGS) -o $@

test: build/wrap-text
	WRAP_TEXT_BIN=build/wrap-text python3 -m unittest discover -s tests -v

sanitize:
	$(MAKE) clean
	$(MAKE) test CC=clang CFLAGS="-std=c17 -O1 -g -Wall -Wextra -Wpedantic -Wconversion -Wshadow -Werror -fsanitize=address,undefined -fno-omit-frame-pointer" LDFLAGS="-fsanitize=address,undefined"

clean:
	rm -rf build
