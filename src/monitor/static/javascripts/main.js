'use strict'

var tableView = null;
var userList = [];
var entryList = [];
var rows = [];

var barchartThroughput = null;
var barchartPuts = null;
var barchartRequests = null;
var barchartExecuteTime = null;

function convert(date) {
    const dateObj = new Date(date);

    return dateObj.getTime();

}

function formatTime(epochTime, adjustment = 1) {
    const date = new Date(epochTime * adjustment);

    date.toLocaleString('en-AU', { timeZone: 'Australia/Sydney' });

    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');

    return `${year}-${month}-${day} ${hours}:${minutes}`;

}

async function command(action, args = []) {
    try {

        document.getElementById("wait-dialog").showModal();

        var message = new Message();

        var response = await message.command(
            document.getElementById("datalake-url").value,
            document.getElementById("datalake-namespace").value,
            document.getElementById("datalake-userid").value,
            document.getElementById("datalake-password").value,
            document.getElementById("identity-url").value,
            document.getElementById("identity-userid").value,
            document.getElementById("identity-password").value,
            document.getElementById("identity-client").value,
            document.getElementById("identity-secret").value,
            action,
            args);

        document.getElementById("wait-dialog").close();
        document.getElementById("command-button").disabled = false;

        document.getElementById("status").innerHTML = `${document.getElementById("datalake-url").value} - connected`;

        await updateStatus();

        enable("server-action");

        document.getElementById("wait-dialog").close();

        return true;

    } catch (exception) {

        if (exception.trace) {
            console.log(exception.trace);
        } else {
            console.log(exception);
        }

        document.getElementById("wait-dialog").close();
        showError(exception.message);

        return false;

    }

}

function enable(className, enable = true) {

    for (var button of document.getElementsByClassName(className)) {
        button.disabled = !enable;
    }

}

function snapshots(requests, request) {
    var stringUtils = new StringUtils();
  
    document.getElementById('request-timeline').replaceChildren();
    
    var template = document.getElementById("snapshot-version").text;
    for (var request of requests) {

        stringUtils.append(template, 'request-timeline',
            {
                "creationTime": request["creationTime"],
                "completionTime": request["completionTime"],
                "request": request["key"],
                "class": "container-selected"
            });

    }

}

async function updateStatus() {
    var message = new Message();
    var response = await message.monitor();
    var table = document.getElementById("log-messages");

    table.replaceChildren();

    for (var entry of response["response"]["log"]) {
        var row = table.insertRow();

        var cell = row.insertCell();

        cell.className = "log-table-item";
        cell.style.fontSize = "11px";
        cell.style.fontWeight = "300";
        cell.style.height = "20px";
        cell.style.fontFamily = "'Courier New', Courier, monospace";

        cell.innerHTML = `${formatTime(entry.time, 1000)}`;

        cell = row.insertCell();
        cell.className = "log-table-item";
        cell.innerHTML = entry.message;

    }

    var counters = response.response.counters;
    var currentHour = new Date(Date.now()).getHours();

    barchartThroughput.setOptimumScale(counters.throughput);

    barchartRequests.setOptimumScale(counters.requests);
    barchartExecuteTime.setOptimumScale(counters.times);
    barchartPuts.setOptimumScale(counters.puts);

    barchartThroughput.draw(counters.throughput, currentHour, "#008080", "#ccffff", 2);
    barchartPuts.draw(counters.puts, currentHour, "#008080", "#ccffff", 0);

    barchartRequests.draw(counters.requests, currentHour, "#008080", "#ccffff", 0);
    barchartExecuteTime.draw(counters.times, currentHour, "#008080", "#ccffff", 0);

    document.getElementById("throughput-label").innerHTML =
        `Throughput Datalake (Units : ${barchartThroughput.precision}) - ${Math.trunc(counters.throughput[currentHour] / barchartThroughput.precision)}`;

   document.getElementById("puts-label").innerHTML =
        `Puts Datalake (Units : ${barchartPuts.precision}) - ${Math.trunc(counters.puts[currentHour] / barchartPuts.precision)}`;

    document.getElementById("executes-label").innerHTML =
        `Requests Retured (Units : ${barchartRequests.precision}) - ${Math.trunc(counters.requests[currentHour] / barchartRequests.precision)}`;

    document.getElementById("execute-times-label").innerHTML =
        `Execution Time (Units : ${barchartExecuteTime.precision}) - ${Math.trunc(counters.times[currentHour] / barchartExecuteTime.precision)}`;

}

function showError(message) {

    document.getElementById("error-message").innerHTML = message;
    document.getElementById("error-dialog").showModal();

}

function clean(id) {
    var element = document.getElementById(id);

    while (element.hasChildNodes()) {
        element.removeChild(element.firstChild);
    }

}

function activate(pages) {

    for (var page of pages) {
        document.getElementById(page["tab"]).classList = page['activate'] ? "rotate-active" : "rotate-inactive";
        document.getElementById(page["panel"]).style.display = page['activate'] ? "inline-block" : "none";
    }

}

function showTable() {

    window.setTimeout(function () {
        if (tableView != null) {
            tableView.setup();
            tableView.resize();
        }
    }, 10);

}

function contains(table, value) {
    for (var i = 0, row; (row = table.rows[i]); i++) {

        if (row.cells[0].innerHTML.trim().toUpperCase() == value.trim().toUpperCase()) {
            return true;
        }

    }
    return false;

}

function addRow(table, value, callback) {
    var row = table.insertRow();

    row.setAttribute("onclick", `window.${callback}('${value}')`, 0);

    var cell = row.insertCell();
    cell.className = "result-table-item";
    cell.style.textWrap = "nowrap";
    cell.style.whiteSpace = "nowrap";

    cell.innerHTML = value;

}


/**
 * Add a index field row
 * 
 * @param {string} table the table element
 * @param {string} field the index field
 */
function addIndexRow(table, field) {

    var newIndex = document.getElementById(table).insertRow();

    newIndex.classList.add("index-attributes");

    var indexCell = newIndex.insertCell(0);
    var trashCell = newIndex.insertCell(1);
    var indexInput = document.createElement("input");

    indexInput.style.fontSize = "14px";
    indexInput.style.width = "380px";
    indexInput.className = "index-field-value";
    indexInput.value = field;

    indexCell.appendChild(indexInput);

    var trashButton = document.createElement("button");
    trashButton.style.fontSize = "14px";
    trashButton.style.width = "80";
    trashButton.innerHTML = "Delete";

    trashButton.addEventListener('click', function (event) {
        var iRow = event.target.parentNode.parentNode.rowIndex;

        document.getElementById(table).deleteRow(iRow);

    });

    trashCell.appendChild(trashButton);

}

/**
 * Respond to the Document 'ready' event
 */
window.onload = async function () {

    document.getElementById("ok-configure").addEventListener('click', async (e) => {

        document.getElementById("action-message").innerHTML = "Hit <b>OK</b> to continute the configuration";

        window.action = async () => {
            await command("configure");
        };

        document.getElementById("action-dialog").showModal();

    });

    document.getElementById("ok-regenerate").addEventListener('click', async (e) => {

        document.getElementById("action-message").innerHTML = "Hit <b>OK</b> to continute to regenerate the token";

        window.action = async () => {
            await command("regenerate");
        };

        document.getElementById("action-dialog").showModal();

    });

    document.getElementById("ok-reset").addEventListener('click', async (e) => {

        document.getElementById("action-message").innerHTML = "Hit <b>OK</b> to continute the reset";

        window.action = async () => {
            await command("reset");
        };

        document.getElementById("action-dialog").showModal();

    });

    document.getElementById("action-dialog-ok").addEventListener('click', async (e) => {

        await window.action();

        document.getElementById("action-dialog").close();

        return false;

    });


    document.getElementById("action-dialog-cancel").addEventListener('click', async (e) => {

        document.getElementById("action-dialog").close();

        return false;

    });


    document.getElementById("ok-connect").addEventListener('click', async (e) => {

        updateStatus();

        enable("server-action");

        document.getElementById("cancel-command-dialog").disabled = false;

        document.getElementById("command-dialog").close();

    });

    document.getElementById("command-button").addEventListener('click', async (e) => {

        document.getElementById("command-dialog").showModal();

        return false;

    });

    document.getElementById("cancel-command-dialog").addEventListener('click', async (e) => {

        document.getElementById("command-dialog").close();

        return false;

    });

    document.getElementById("refresh-button").addEventListener('click', async (e) => {

        updateStatus();

    });

    document.getElementById("info-button").addEventListener('click', async (e) => {

        renderjson.setShowToLevel(3);

        try {
            document.getElementById("wait-dialog").showModal();

            var message = new Message();
            var response = await message.command(
                document.getElementById("datalake-url").value,
                document.getElementById("datalake-namespace").value,
                document.getElementById("datalake-userid").value,
                document.getElementById("datalake-password").value,
                document.getElementById("identity-url").value,
                document.getElementById("identity-userid").value,
                document.getElementById("identity-password").value,
                document.getElementById("identity-client").value,
                document.getElementById("identity-secret").value,
                "report",
                []);

            for (var column of response["response"]["output"][0]["message"]) {

                if (column["col"] == "json:control") {
                    var tokens = JSON.parse(column["val"]);
                    document.getElementById("token-view").replaceChildren();
                    document.getElementById("token-view").appendChild(renderjson(tokens));
                
                } else if (column["col"] == "json:indexes") {
                    var indexes = JSON.parse(column["val"]);
                    
                    document.getElementById("indexes-view").replaceChildren();
                    document.getElementById("indexes-view").appendChild(renderjson(indexes));
 
                } else if (column["col"] == "json:checkpoint") {
                    var checkpoint = JSON.parse(column["val"]);

                    if (checkpoint["time"] != 0) {
                        checkpoint["converted"] = formatTime(checkpoint["time"]);
                    }

                    document.getElementById("checkpoint-view").replaceChildren();
                    document.getElementById("checkpoint-view").appendChild(renderjson(checkpoint));

                }

            }

            document.getElementById("wait-dialog").close();
            document.getElementById("info-dialog").showModal();

        } catch (exception) {

            if (exception.trace) {
                console.log(exception.trace);
            } else {
                console.log(exception);
            }

            document.getElementById("wait-dialog").close();
            showError(exception.message);

        }

    });

    document.getElementById("index-button").addEventListener('click', async (e) => {

        document.getElementById("index-dialog").showModal();

    });

    document.getElementById("snapshot-button").addEventListener('click', async (e) => {

        document.getElementById("snapshot-dialog").showModal();

    });

    document.getElementById("close-info-dialog").addEventListener('click', async (e) => {

        document.getElementById("info-dialog").close();

    });

    document.getElementById("ok-snapshot-dialog").addEventListener('click', async (e) => {

        try {

            var message = new Message();

            message.snapshot(
                document.getElementById("datalake-url").value,
                document.getElementById("datalake-namespace").value,
                document.getElementById("datalake-userid").value,
                document.getElementById("datalake-password").value,
                document.getElementById("identity-url").value,
                document.getElementById("identity-userid").value,
                document.getElementById("identity-password").value,
                document.getElementById("identity-client").value,
                document.getElementById("identity-secret").value,
                document.getElementById("thread-count").value,
                document.getElementById("batch-size").value,
                document.getElementById("scan-size").value,
                document.getElementById("page-size").value,
                document.getElementById("check-frequency").value,
                document.getElementById("retain-period").value
            );

            window.setTimeout(function () {
                updateStatus();
            }, 1000);

            document.getElementById("snapshot-dialog").close();

        } catch (exception) {

            if (exception.trace) {
                console.log(exception.trace);
            } else {
                console.log(exception);
            }

            document.getElementById("wait-dialog").close();
            showError(exception.message);

            window.setTimeout(function () {
                updateStatus();
            }, 1000);

        }

    });

    document.getElementById("ok-index-dialog").addEventListener('click', async (e) => {
        var indexes = [];

        var rows = document.getElementsByClassName("index-field-value")

        for (var row of rows) {

            if(row.value.length > 0) {
                indexes.push(row.value);
            }

        }

        document.getElementById("action-message").innerHTML = "Hit <b>OK</b> to continute the index";
          
        var status = await command("index", indexes);

        if (status) {
            document.getElementById("index-dialog").close();
        }

    });

    document.getElementById("cancel-index-dialog").addEventListener('click', async (e) => {

        document.getElementById("index-dialog").close();

    });

    document.getElementById("cancel-snapshot-dialog").addEventListener('click', async (e) => {

        document.getElementById("snapshot-dialog").close();

    });

    document.getElementById("add-index-field").addEventListener('click', async (e) => {

        addIndexRow("index-fields", "");

    });

    document.getElementById(`thread-count`).addEventListener('input', function (event) {
         document.getElementById(`thread-count-value`).innerHTML = event.target.value;
    });

    document.getElementById(`batch-size`).addEventListener('input', function (event) {
        document.getElementById(`batch-size-value`).innerHTML = event.target.value;
    });

    document.getElementById(`scan-size`).addEventListener('input', function (event) {
         document.getElementById(`scan-size-value`).innerHTML = event.target.value;
    });

    document.getElementById(`page-size`).addEventListener('input', function (event) {
        document.getElementById(`page-size-value`).innerHTML = event.target.value;
    });

    document.getElementById(`check-frequency`).addEventListener('input', function (event) {
        document.getElementById(`check-frequency-value`).innerHTML = event.target.value;
    });
    
    document.getElementById(`retain-period`).addEventListener('input', function (event) {
        document.getElementById(`retain-period-value`).innerHTML = event.target.value;
    });
    
    document.getElementById(`task-timeout`).addEventListener('input', function (event) {
        document.getElementById(`task-timeout-value`).innerHTML = event.target.value;
    });
    document.getElementById(`command-dialog`).addEventListener('input', function (event) {
        const container = document.getElementById('command-dialog');
        const fields = container.querySelectorAll('input, select, textarea');

        var enabled = Array.from(fields).every(field => field.checkValidity());

        for (var button of container.getElementsByClassName('server-command')) {
            button.disabled = !enabled;
        }

    });

    barchartThroughput = new BarChart("throughput-container", 24);
    barchartPuts = new BarChart("puts-container", 24);
    barchartRequests = new BarChart("executes-container", 24);
    barchartExecuteTime = new BarChart("execute-times-container", 24);

    var panelView = new PanelView("static/images/expand.svg", "static/images/contract.svg");

    panelView.decorate("throughput-collapse", "throughput-collapse-image", "throughput-container", true);
    panelView.decorate("puts-collapse", "throughput-collapse-image", "throughput-container", true);
    panelView.decorate("executes-collapse", "executes-collapse-image", "executes-container", true);
    panelView.decorate("execute-times-collapse", "execute-times-collapse-image", "execute-times-container", true);

    activateTabs('configuration-tabs', 'datalake-panel', 'configuration-tab1');
    activateTabs('info-tabs', 'summary-panel', 'info-tab1');
    activateTabs('message-tabs', 'message-panel', 'message-tab1');

    document.getElementById("command-dialog").showModal();

}
