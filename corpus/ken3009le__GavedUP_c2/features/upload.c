#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <curl/curl.h>
#include "upload.h"
#include "../lib/base64.h"  //
#define GITHUB_TOKEN_FILE "token.token"
#define GITHUB_USERNAME   "ken3009le"
#define GITHUB_REPO       "ken3009le.github.io"
#define GITHUB_BRANCH     "main"

char* load_token() {
    FILE* f = fopen(GITHUB_TOKEN_FILE, "r");
    if (!f) return NULL;

    char* token = malloc(256);
    if (!token) {
        fclose(f);
        return NULL;
    }

    fgets(token, 255, f);
    fclose(f);
    token[strcspn(token, "\r\n")] = 0; // Remove newline
    return token;
}

int upload_result_to_github(const char* content, const char* filename) {
    char path[512];
    snprintf(path, sizeof(path), "logs/%s", filename);

    char* token = load_token();
    if (!token) {
        fprintf(stderr, "[x] Failed to load GitHub token.\n");
        return 0;
    }

    char* encoded = base64_encode((const unsigned char*)content, strlen(content));
    if (!encoded) {
        fprintf(stderr, "[x] Failed to base64 encode content.\n");
        free(token);
        return 0;
    }

    char* json = malloc(strlen(encoded) + 512);
    if (!json) {
        free(encoded);
        free(token);
        return 0;
    }

    snprintf(json, strlen(encoded) + 512,
        "{ \"message\": \"upload\", \"content\": \"%s\", \"branch\": \"%s\" }",
        encoded, GITHUB_BRANCH);

    char url[512];
    snprintf(url, sizeof(url),
        "https://api.github.com/repos/%s/%s/contents/%s",
        GITHUB_USERNAME, GITHUB_REPO, path);

    CURL* curl = curl_easy_init();
    if (!curl) {
        free(encoded);
        free(json);
        free(token);
        return 0;
    }

    struct curl_slist* headers = NULL;
    char auth_header[300];
    snprintf(auth_header, sizeof(auth_header), "Authorization: token %s", token);

    headers = curl_slist_append(headers, "User-Agent: upload-agent");
    headers = curl_slist_append(headers, "Content-Type: application/json");
    headers = curl_slist_append(headers, auth_header);

    curl_easy_setopt(curl, CURLOPT_URL, url);
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, json);
    curl_easy_setopt(curl, CURLOPT_CUSTOMREQUEST, "PUT");
    curl_easy_setopt(curl, CURLOPT_CAINFO, "C:/curl/cacert.pem");


    CURLcode res = curl_easy_perform(curl);

    if (res != CURLE_OK) {
        fprintf(stderr, "[x] Upload failed: %s\n", curl_easy_strerror(res));
    } else {
        printf("[+] Uploaded %s to GitHub successfully.\n", filename);
    }

    curl_easy_cleanup(curl);
    curl_slist_free_all(headers);
    free(encoded);
    free(json);
    free(token);

    return (res == CURLE_OK);
}
