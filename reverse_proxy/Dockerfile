FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY . .
RUN go mod init reverse-proxy 2>/dev/null || true && \
    go mod tidy 2>/dev/null || true && \
    CGO_ENABLED=0 go build -ldflags="-s -w" -o reverse-proxy .

FROM alpine:latest
RUN apk --no-cache add ca-certificates wget
WORKDIR /app
COPY --from=builder /app/reverse-proxy .
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1
ENTRYPOINT ["./reverse-proxy"]
CMD ["8080", "config.json"]