#!/bin/bash
version=1.4.2

rm build/*

# Windows amd64
goos=windows
goarch=amd64
GOOS=$goos GOARCH=$goarch go build -o wcvs.exe
zip build/web-cache-vulnerability-scanner_"$version"_"$goos"_"$goarch".zip wcvs.exe

# Linux amd64
goos=linux
goarch=amd64
GOOS=$goos GOARCH=$goarch go build -o wcvs
tar cfvz build/web-cache-vulnerability-scanner_"$version"_"$goos"_"$goarch".tar.gz wcvs

# Linux arm64
goos=linux
goarch=arm64
GOOS=$goos GOARCH=$goarch go build -o wcvs
tar cfvz build/web-cache-vulnerability-scanner_"$version"_"$goos"_"$goarch".tar.gz wcvs

# Darwin/MacOS amd64
goos=darwin
goarch=amd64
GOOS=$goos GOARCH=$goarch go build -o wcvs
tar cfvz build/web-cache-vulnerability-scanner_"$version"_"$goos"_"$goarch".tar.gz wcvs

# Darwin/MacOS arm64
goos=darwin
goarch=arm64
GOOS=$goos GOARCH=$goarch go build -o wcvs
tar cfvz build/web-cache-vulnerability-scanner_"$version"_"$goos"_"$goarch".tar.gz wcvs

# FreeBSD amd64
goos=freebsd
goarch=amd64
GOOS=$goos GOARCH=$goarch go build -o wcvs
tar cfvz build/web-cache-vulnerability-scanner_"$version"_"$goos"_"$goarch".tar.gz wcvs

# OpenBSD amd64
goos=openbsd
goarch=amd64
GOOS=$goos GOARCH=$goarch go build -o wcvs
tar cfvz build/web-cache-vulnerability-scanner_"$version"_"$goos"_"$goarch".tar.gz wcvs

# reset GOOS and GOARCH
set GOOS=
set GOARCH=

# remove wcvs
rm wcvs
rm wcvs.exe

# generate checksum file
find build/ -type f  \( -iname "*.tar.gz" -or -iname "*.zip" \) -exec sha256sum {} + > build/web-cache-vulnerability-scanner_"$version"_checksums_sha256.txt
