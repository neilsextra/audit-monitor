function Message() {

    this._command = function (datalakeUrl, datalakeNamespace, datalakeUserid, datalakePassword,
        identityUrl, identityUserid, identityPassword, identityClient, identitySecret,
        command, args) {

        return new Promise((accept, reject) => {
            let parmURL = `/command?action=${encodeURIComponent(command)}`

            for (var arg of args) {
                parmURL += `&arg=${encodeURIComponent(arg)}`;
            }

            var xhttp = new XMLHttpRequest();

            xhttp.open("GET", parmURL, true);

            xhttp.setRequestHeader("datalake-url", datalakeUrl);
            xhttp.setRequestHeader("datalake-namespace", datalakeNamespace);
            xhttp.setRequestHeader("datalake-userid", datalakeUserid);
            xhttp.setRequestHeader("datalake-password", datalakePassword);
            xhttp.setRequestHeader("identity-url", identityUrl);
            xhttp.setRequestHeader("identity-userid", identityUserid);
            xhttp.setRequestHeader("identity-password", identityPassword);
            xhttp.setRequestHeader("identity-client", identityClient);
            xhttp.setRequestHeader("identity-secret", identitySecret);

            xhttp.onreadystatechange = async function () {
                xhttp.onload = function () {

                    if (this.readyState === 4 && this.status === 200) {
                        var response = JSON.parse(xhttp.response);

                        accept({
                            status: this.status,
                            response: response
                        });

                    } else {

                        reject({
                            status: this.status,
                            message: this.statusText
                        });

                    }

                };

                xhttp.onerror = function () {
                };

            }

            xhttp.send();

        });

    }.bind(this);

    this._report = function (datalakeUrl, datalakeNamespace, datalakeUserid, datalakePassword,
        identityUrl) {

        return new Promise((accept, reject) => {
            let parmURL = `/report`

            var xhttp = new XMLHttpRequest();

            xhttp.open("GET", parmURL, true);

            xhttp.setRequestHeader("datalake-url", datalakeUrl);
            xhttp.setRequestHeader("datalake-namespace", datalakeNamespace);
            xhttp.setRequestHeader("datalake-userid", datalakeUserid);
            xhttp.setRequestHeader("datalake-password", datalakePassword);
            xhttp.setRequestHeader("identity-url", identityUrl);
  
            xhttp.onreadystatechange = async function () {
                xhttp.onload = function () {

                    if (this.readyState === 4 && this.status === 200) {
                        var response = JSON.parse(xhttp.response);

                        accept({
                            status: this.status,
                            response: response
                        });

                    } else {

                        reject({
                            status: this.status,
                            message: this.statusText
                        });

                    }

                };

                xhttp.onerror = function () {
                };

            }

            xhttp.send();

        });

    }.bind(this);

    this._monitor = function () {

        return new Promise((accept, reject) => {
            let parmURL = `/monitor`;

            var xhttp = new XMLHttpRequest();

            xhttp.open("GET", parmURL, true);

            xhttp.onreadystatechange = async function () {
                xhttp.onload = function () {

                    if (this.readyState === 4 && this.status === 200) {
                        var response = JSON.parse(xhttp.response);

                        accept({
                            status: this.status,
                            response: response
                        });

                    } else {

                        reject({
                            status: this.status,
                            message: this.statusText
                        });

                    }

                };

                xhttp.onerror = function () {
                };

            }

            xhttp.send();

        });

    }.bind(this);

    this._snapshot = function (datalakeUrl, datalakeNamespace, datalakeUserid, datalakePassword,
        identityUrl, identityUserid, identityPassword, identityClient, identitySecret,
        threads, batchsize, scanSize, pagesize, frequency, retain, timeout) {

        return new Promise((accept, reject) => {
            let parmURL = `/snapshot?threads=${threads}&batch-size=${batchsize}&scan-size=${scanSize}&page-size=${pagesize}` +
                          `&check-frequency=${frequency}&retain-period=${retain}&task-timeout=${timeout}`;
            var xhttp = new XMLHttpRequest();

            xhttp.open("GET", parmURL, true);

            xhttp.setRequestHeader("datalake-url", datalakeUrl);
            xhttp.setRequestHeader("datalake-namespace", datalakeNamespace);
            xhttp.setRequestHeader("datalake-userid", datalakeUserid);
            xhttp.setRequestHeader("datalake-password", datalakePassword);
            xhttp.setRequestHeader("identity-url", identityUrl);
            xhttp.setRequestHeader("identity-userid", identityUserid);
            xhttp.setRequestHeader("identity-password", identityPassword);
            xhttp.setRequestHeader("identity-client", identityClient);
            xhttp.setRequestHeader("identity-secret", identitySecret);

            xhttp.onreadystatechange = async function () {
                xhttp.onload = function () {

                    if (this.readyState === 4 && this.status === 200) {
                        var response = JSON.parse(xhttp.response);

                        accept({
                            status: this.status,
                            response: response
                        });

                    } else {

                        reject({
                            status: this.status,
                            message: this.statusText
                        });

                    }

                };

                xhttp.onerror = function () {
                };

            }

            xhttp.send();

        });

    }.bind(this);

}

Message.prototype.command = function (datalakeUrl, datalakeNamespace,
    datalakeUserid, datalakePassword,
    identityUrl, identityUserid, identityPassword,
    identityClient, identitySecret,
    action,
    args) {

    return this._command(datalakeUrl, datalakeNamespace,
        datalakeUserid, datalakePassword,
        identityUrl, identityUserid, identityPassword,
        identityClient, identitySecret,
        action,
    args);

}

Message.prototype.snapshot = function (datalakeUrl, datalakeNamespace,
    datalakeUserid, datalakePassword,
    identityUrl, identityUserid, identityPassword,
    identityClient, identitySecret,
    threads, batchsize, scanSize, pagesize, 
    frequency, retain, timeout) {
  
    return this._snapshot(datalakeUrl, datalakeNamespace,
        datalakeUserid, datalakePassword,
        identityUrl, identityUserid, identityPassword,
        identityClient, identitySecret,
        threads, batchsize, scanSize, pagesize, 
        frequency, retain, timeout);

}

Message.prototype.monitor = function () {

    return this._monitor();

}
