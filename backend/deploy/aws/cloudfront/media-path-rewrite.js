function handler(event) {
    var request = event.request;
    var match = request.uri.match(/^\/(free|premium|restricted)(\/.+)$/);

    if (!match) {
        return {
            statusCode: 404,
            statusDescription: "Not Found"
        };
    }

    request.uri = match[2];
    return request;
}
