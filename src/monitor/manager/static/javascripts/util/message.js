function Message() {

    this._command = function (datalakeUrl, datalakeNamespace, datalakeUserid, datalakePassword,
        identityUrl, identityUserid, identityPassword, identityClientId, identitySecret,
        command) {

        return new Promise((accept, reject) => {
            let parmURL = `/command?action=${encodeURIComponent(command)}`

            var xhttp = new XMLHttpRequest();

            xhttp.open("GET", parmURL, true);

            xhttp.setRequestHeader("datalake-url", datalakeUrl);
            xhttp.setRequestHeader("datalake-namespace", datalakeNamespace);
            xhttp.setRequestHeader("datalake-userid", datalakeUserid);
            xhttp.setRequestHeader("datalake-password", datalakePassword);
            xhttp.setRequestHeader("identity-url", identityUrl);
            xhttp.setRequestHeader("identity-userid", identityUserid);
            xhttp.setRequestHeader("identity-password", identityPassword);
            xhttp.setRequestHeader("identity-clientid", identityClientId);
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

    this._execute = function (datalakeUrl, datalakeNamespace, datalakeUserid, datalakePassword,
        identityUrl, identityUserid, identityPassword, identityClientId, identitySecret,
        threads, batchsize, checkpoint, pagesize) {

        return new Promise((accept, reject) => {
            let parmURL = `/execute?threads=${threads}&batch-size=${batchsize}&checkpoint=${checkpoint}&page-size=${pagesize}`

            var xhttp = new XMLHttpRequest();

            xhttp.open("GET", parmURL, true);

            xhttp.setRequestHeader("datalake-url", datalakeUrl);
            xhttp.setRequestHeader("datalake-namespace", datalakeNamespace);
            xhttp.setRequestHeader("datalake-userid", datalakeUserid);
            xhttp.setRequestHeader("datalake-password", datalakePassword);
            xhttp.setRequestHeader("identity-url", identityUrl);
            xhttp.setRequestHeader("identity-userid", identityUserid);
            xhttp.setRequestHeader("identity-password", identityPassword);
            xhttp.setRequestHeader("identity-clientid", identityClientId);
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
    identityClientId, identitySecret,
    action) {
    console.log(`[${action}] Userid: ${identityUserid}`)

    return this._command(datalakeUrl, datalakeNamespace,
        datalakeUserid, datalakePassword,
        identityUrl, identityUserid, identityPassword,
        identityClientId, identitySecret,
        action);

}

Message.prototype.reset = function (datalakeUrl, datalakeNamespace,
    datalakeUserid, datalakePassword,
    identityUrl, identityUserid, identityPassword,
    identityClientId, identitySecret) {
    console.log(`Userid: ${identityUserid} - Password: ${identityPassword}`)

    return this._command(datalakeUrl, datalakeNamespace,
        datalakeUserid, datalakePassword,
        identityUrl, identityUserid, identityPassword,
        identityClientId, identitySecret,
        "reset");

}

Message.prototype.regenerate = function (datalakeUrl, datalakeNamespace,
    datalakeUserid, datalakePassword,
    identityUrl, identityUserid, identityPassword,
    identityClientId, identitySecret) {
    console.log(`Userid: ${identityUserid} - Password: ${identityPassword}`)

    return this._command(datalakeUrl, datalakeNamespace,
        datalakeUserid, datalakePassword,
        identityUrl, identityUserid, identityPassword,
        identityClientId, identitySecret,
        "regenerate");

}

Message.prototype.execute = function (datalakeUrl, datalakeNamespace,
    datalakeUserid, datalakePassword,
    identityUrl, identityUserid, identityPassword,
    identityClientId, identitySecret,
    threads, batchsize, checkpoint, pagesize) {
  
    return this._execute(datalakeUrl, datalakeNamespace,
        datalakeUserid, datalakePassword,
        identityUrl, identityUserid, identityPassword,
        identityClientId, identitySecret,
        threads, batchsize, checkpoint, pagesize);

}

Message.prototype.monitor = function () {

    return this._monitor();

}
