#include "tcp_server.h"

int tcp_server_run(void *arg, socket_server_callback callback, int port, size_t buf_size) {
    struct socket_server server = {0};
    struct socket_server client = {0};
    socklen_t addr_len;

    // allocate buffer
    if ((server.buf = malloc(buf_size)) == NULL) {
        perror("Failed to allocate buffer");
        goto error;
    }

    // open socket
    if ((server.socket_fd = socket(AF_INET, SOCK_STREAM, 0)) < 0) {
        perror("Could not open socket");
        goto error;
    }

    // configure reuse socket
    const int enable = 1;
    if (setsockopt(server.socket_fd, SOL_SOCKET, SO_REUSEADDR, &enable, sizeof(enable)) < 0) {
        perror("setsockopt(SO_REUSEADDR) failed");
        goto error;
    }
    if (setsockopt(sockfd, SOL_SOCKET, SO_REUSEPORT, &enable, sizeof(enable)) < 0)  {
        perror("setsockopt(SO_REUSEPORT) failed");
        goto error;
    }

    // bind address
    memset(&server.addr, 0, sizeof(server.addr));
    server.addr.sin_family = AF_INET;
    server.addr.sin_port = htons(port);
    server.addr.sin_addr.s_addr = htonl(INADDR_ANY);
    if (bind(server.socket_fd, (struct sockaddr *) &server.addr, sizeof(server.addr)) < 0) {
        perror("Could not bind socket to port");
        goto error;
    }

    // listen client
    if ((listen(server.socket_fd, 5)) != 0) {
        perror("Listen failed");
        goto error;
    }

    // accept client
    addr_len = sizeof(client.addr);
    client.socket_fd = accept(server.socket_fd, (struct sockaddr *) &client.addr, &addr_len);
    if (client.socket_fd < 0) {
        perror("Server accept failed");
        goto error;
    }

    // start server loop
    printf("Serving on port %d ...\n", port);
    while (1) {
        // wait for a packet
        int received_len = recv(client.socket_fd, server.buf, buf_size, 0);
        if (received_len < 0) {
            perror("Failed to receive data from socket");
            goto error;
        }

        dbg_printf("Received %d byte packet\n", received_len);
        dbg_memdump(server.buf, received_len);

        // process the incoming data
        int response_len = callback(arg, server.buf, buf_size, received_len);
        if (response_len < 0) {
            fprintf(stderr, "Error while processing a packet from %s:%d\n",
                    inet_ntoa(client.addr), port);
            goto error;
        }

        // do not respond if there is no response data?
        if (response_len == 0)
            continue;

        // send the response
        dbg_printf("Sending %d byte response\n", response_len);
        dbg_memdump(server.buf, response_len);

        if (sendto(client.socket_fd, server.buf, response_len, 0) == -1) {
            char msg[100];
            sprintf(msg, "Failed to reply to %s:%d", inet_ntoa(client.addr), port);
            perror(msg);
            goto error;
        }
    }

    assert(0);  // should never get here

error:
    printf("Aborting\n");
    if (client.socket_fd > 0) {
        close(client.socket_fd);
    }
    if (server.socket_fd > 0) {
        close(server.socket_fd);
    }
    if (server.buf != NULL) {
        free(server.buf);
    }
    return -1;
}