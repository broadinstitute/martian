#!/bin/zsh

set -e

GOOS=linux GOARCH=amd64 GO111MODULE=on go build -trimpath \
  -ldflags "-X 'github.com/martian-lang/martian/martian/util.__VERSION__=$(git describe --tags --always --dirty)' -X github.com/martian-lang/martian/martian/util.__RELEASE__='false'" \
  -o bin/ ./cmd/...

tar -czf martian.tar.gz -T sync_files.txt

gcloud storage cp martian.tar.gz gs://cds-perturbseq-misc/
