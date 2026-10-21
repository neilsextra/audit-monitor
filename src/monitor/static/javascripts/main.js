'use strict'

var tableView = null;
var userList = [];
var entryList = [];
var rows = [];

var barchartWrites = null;
var barchartThroughput = null;
var barchartExecutes = null;
var barchartExecuteTimes = null;

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

async function command(action) {
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
            document.getElementById("identity-clientid").value,
            document.getElementById("identity-secret").value,
            action);

        document.getElementById("wait-dialog").close();

        document.getElementById("command-dialog").close();

        document.getElementById("cancel-command-dialog").style.visibility = "visible";
        document.getElementById("command-button").disabled = false;

        document.getElementById("status").innerHTML = `${document.getElementById("datalake-url").value} - connected`;

        await updateStatus();

        enable("server-action");

        document.getElementById("wait-dialog").close();
        document.getElementById("command-dialog").close();

    } catch (exception) {

        if (exception.trace) {
            console.log(exception.trace);
        } else {
            console.log(exception);
        }

        document.getElementById("wait-dialog").close();
        showError(exception.message);

    }

}

function enable(className, enable = true) {

    for (var button of document.getElementsByClassName(className)) {
        button.disabled = !enable;
    }

}

async function updateStatus() {
    var message = new Message();
    var response = await message.monitor();

    console.log(JSON.stringify(response));

    var table = document.getElementById("log-messages");

    table.replaceChildren();

    for (var entry of response["response"]["log"]) {
        var row = table.insertRow();

        var cell = row.insertCell();

        cell.className = "log-table-item";
        cell.style.width = "100px";

        cell.innerHTML = formatTime(entry.time, 1000);

        cell = row.insertCell();

        cell.className = "log-table-item";
        cell.innerHTML = entry.message;

    }
    
    var counters = response.response.counters;
    var currentHour = new Date(Date.now()).getHours();

    console.log(JSON.stringify(counters));

    barchartWrites.setOptimumScale(counters.puts);
    barchartThroughput.setOptimumScale(counters.throughput);
 
    barchartExecutes.setOptimumScale(counters.requests);
    barchartExecuteTimes.setOptimumScale(counters.transactions);

    barchartWrites.draw(counters.puts, currentHour, "#008080", "#ccffff", 0);
    barchartThroughput.draw(counters.throughput, currentHour, "#008080", "#ccffff", 2);
  
    barchartExecutes.draw(counters.requests, currentHour, "#008080", "#ccffff", 0);
    barchartExecuteTimes.draw(counters.throughput, currentHour, "#008080", "#ccffff", 0);

    document.getElementById("writes-label").innerHTML =
        `Writes Datalake (Units : ${barchartWrites.precision}) - ${Math.trunc(counters.puts[currentHour] / barchartWrites.precision)}`;
    document.getElementById("throughput-label").innerHTML =
        `Throughput Datalake (Units : ${barchartThroughput.precision}) - ${Math.trunc(counters.throughput[currentHour] / barchartThroughput.precision)}`;

    document.getElementById("executes-label").innerHTML =
        `Execution (Units : ${barchartExecutes.precision}) - ${Math.trunc(counters.requests[currentHour] / barchartExecutes.precision)}`;

    document.getElementById("execute-times-label").innerHTML =
        `Execution Times (Units : ${barchartExecuteTimes.precision}) - ${Math.trunc(counters.transactions[currentHour] / barchartExecuteTimes.precision)}`;

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
 * Respond to the Document 'ready' event
 */
window.onload = async function () {

    document.getElementById("ok-configure").addEventListener('click', async (e) => {

        await command("configure");

    });

    document.getElementById("ok-connect").addEventListener('click', async (e) => {

        updateStatus();

        enable("server-action");

        document.getElementById("command-dialog").close();

    });

    document.getElementById("ok-reset").addEventListener('click', async (e) => {

        await command("configure");

    });

    document.getElementById("ok-regenerate").addEventListener('click', async (e) => {

        await command("regenerate");

    });

    document.getElementById("command-button").addEventListener('click', async (e) => {

        document.getElementById("command-dialog").showModal();

    });

    document.getElementById("cancel-command-dialog").addEventListener('click', async (e) => {

        document.getElementById("command-dialog").close();

    });

    document.getElementById("refresh-button").addEventListener('click', async (e) => {

        updateStatus();

    });

    document.getElementById("execute-button").addEventListener('click', async (e) => {

        document.getElementById("execute-dialog").showModal();

    });

    document.getElementById("ok-execute-dialog").addEventListener('click', async (e) => {

        try {
 
            var message = new Message();

            message.execute(
                document.getElementById("datalake-url").value,
                document.getElementById("datalake-namespace").value,
                document.getElementById("datalake-userid").value,
                document.getElementById("datalake-password").value,
                document.getElementById("identity-url").value,
                document.getElementById("identity-userid").value,
                document.getElementById("identity-password").value,
                document.getElementById("identity-clientid").value,
                document.getElementById("identity-secret").value,
                document.getElementById("thread-count").value,
                document.getElementById("batch-size").value,
                document.getElementById("checkpoint-count").value,
                document.getElementById("page-size").value
            );

            window.setTimeout(function () {
                 updateStatus();
            }, 1000);

            document.getElementById("execute-dialog").close();

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

    document.getElementById("cancel-execute-dialog").addEventListener('click', async (e) => {

        document.getElementById("execute-dialog").close();

    });

    document.getElementById(`thread-count`).addEventListener('input', function (event) {
        var directory = window.directory;
        document.getElementById(`thread-count-value`).innerHTML = event.target.value;
    });

    document.getElementById(`batch-size`).addEventListener('input', function (event) {
        var directory = window.directory;
        document.getElementById(`batch-size-value`).innerHTML = event.target.value;
    });

    document.getElementById(`checkpoint-count`).addEventListener('input', function (event) {
        var directory = window.directory;
        document.getElementById(`checkpoint-count-value`).innerHTML = event.target.value;
    });

    document.getElementById(`page-size`).addEventListener('input', function (event) {
        var directory = window.directory;
        document.getElementById(`page-size-value`).innerHTML = event.target.value;
    });

    document.getElementById(`command-dialog`).addEventListener('input', function (event) {
        const container = document.getElementById('command-dialog');
        const fields = container.querySelectorAll('input, select, textarea');

        var enabled = Array.from(fields).every(field => field.checkValidity());

        for (var button of container.getElementsByClassName('server-command')) {
            button.disabled = !enabled;
        }

    });

    barchartWrites = new BarChart("writes-container", 24);
    barchartThroughput = new BarChart("throughput-container", 24);
    barchartExecutes = new BarChart("executes-container", 24);
    barchartExecuteTimes = new BarChart("execute-times-container", 24);

    var panelView = new PanelView("static/images/expand.svg", "static/images/contract.svg");

    panelView.decorate("writes-collapse", "writes-collapse-image", "writes-container", true);
    panelView.decorate("throughput-collapse", "throughput-collapse-image", "throughput-container", true);
    panelView.decorate("executes-collapse", "executes-collapse-image", "executes-container", true);
    panelView.decorate("execute-times-collapse", "execute-times-collapse-image", "execute-times-container", true);

    activateTabs('configuration-tabs', 'datalake-panel', 'configuration-tab1');

    document.getElementById("command-dialog").showModal();

}
