// qwebchannel.js (QtWebChannel 5.15.2 기준 간략화 버전)
(function() {
    if (typeof QWebChannel === "function") {
        return;
    }

    window.QWebChannel = function(transport, initCallback) {
        var channel = this;
        this.transport = transport;
        this.objects = {};

        var execCallbacks = {};
        var execId = 0;

        this.send = function(data) {
            transport.send(JSON.stringify(data));
        };

        this.exec = function(data, callback) {
            if (!callback) {
                this.send(data);
                return;
            }
            if (++execId === Number.MAX_VALUE) execId = 1;
            data.id = execId;
            execCallbacks[data.id] = callback;
            this.send(data);
        };

        transport.onmessage = function(event) {
            var data = JSON.parse(event.data);
            if (data.type === "signal") {
                var object = channel.objects[data.object];
                if (object && object[data.signal]) {
                    object[data.signal].apply(object, data.args);
                }
            } else if (data.type === "response") {
                if (execCallbacks[data.id]) {
                    execCallbacks[data.id](data.data);
                    delete execCallbacks[data.id];
                }
            }
        };

        this.exec({type: "init"}, function(data) {
            for (var objectName in data.objects) {
                var object = data.objects[objectName];
                channel.objects[objectName] = object;
            }
            if (initCallback) {
                initCallback(channel);
            }
        });
    };
})();
