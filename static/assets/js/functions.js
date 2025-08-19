document.addEventListener('DOMContentLoaded', function () {
    fetch('/load_state')
        .then(response => response.json())
        .then(data => updateButtons(data))
        .catch(error => console.error('Error loading state:', error));
});

// adds tab id to url so that we can deep link to it with redirects and reloads.
$(document).ready(() => {
    let tabUrl = location.href.replace(/\/$/, "");
    if (location.hash) {
        const hash = tabUrl.split("#");
        $('a[href="#' + hash[1] + '"]').tab("show");
        tabUrl = location.href.replace(/#/, "#");
        history.replaceState(null, null, tabUrl);
    }
    $('a[data-toggle="tab"]').on("click", function () {
        let newUrl;
        const hash = $(this).attr("href");
        newUrl = tabUrl.replace(/#.*$/, "") + hash;
        history.replaceState(null, null, newUrl);
    });
});

document.getElementById('configForm').addEventListener('submit', function (event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    const data = {};
    formData.forEach((value, key) => {
        data[key] = value;
    });
    fetch('/update_config', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: new URLSearchParams(data)
    }).then(response => response.json())
        .then(data => {
            alert(data.message);
            setTimeout(() => {
                window.location.reload(); // Refresh the browser window
            }, 500);
        })
        .catch(error => console.error('Error:', error));
});

function sendRequest(endpoint) {
    fetch(endpoint, {
        method: 'POST'
    })
        .then(response => response.json())
        .then(data => {
            alert(data.message);
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Failed to send request.');
        });
}

function toggle(action) {
    fetch('/toggle_' + action, {
        method: 'POST'
    })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to toggle ' + action);
            }
            return response.json();
        })
        .then(() => {
            window.location.reload(); // Refresh the browser window
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Failed to toggle ' + action + '.');
        });
}

document.getElementById("show_key").addEventListener("click", function (e) {
    if (document.getElementById("show_key").innerText === "hide") {
        document.getElementById("show_key").innerText = "show";
        document.getElementById("STREAM_KEY").setAttribute('type', 'password');
    } else {
        document.getElementById("show_key").innerText = "hide";
        document.getElementById("STREAM_KEY").setAttribute('type', 'text');
    }
}, false);

// Disable buttons until recording has finished remux process. 
// When the page reloads it will supdateButtons() and et the state to 'Start Recording'
document.addEventListener("DOMContentLoaded", function () {
    const recordButton = document.getElementById('record_button');
    const recordStreamButton = document.getElementById('stream_record_button');
    const buttons = document.querySelectorAll('button');

    recordButton.addEventListener("click", function () {
        if (recordButton.textContent === 'Stop Record') {
            recordButton.textContent = 'Finalizing Recording...';
        } else {
            recordButton.textContent = 'Starting...';
        }
        // Disable ALL buttons
        buttons.forEach(button => {
            button.disabled = true;
            button.classList.add('disabled');
        });
    });

    recordStreamButton.addEventListener("click", function () {
        if (recordStreamButton.textContent === 'Stop Stream & Record') {
            recordStreamButton.textContent = 'Finalizing Recording...';
        } else {
            recordStreamButton.textContent = 'Starting...';
        }
        // Disable ALL buttons
        buttons.forEach(button => {
            button.disabled = true;
            button.classList.add('disabled');
        });
    });
});

function updateButtons(state) {
    const recordingActions = document.querySelectorAll('.recordingActions');
    const updateButton = document.querySelectorAll('.btn-primary');
    const inputs = document.querySelectorAll('input');
    const selects = document.querySelectorAll('select');
    const buttons = {
        stream: document.getElementById('stream_button'),
        stream_record: document.getElementById('stream_record_button'),
        record: document.getElementById('record_button'),
        file_stream: document.getElementById('file_stream_button')
    };

    if (state.streaming) {
        buttons.stream.classList.remove('btn-success');
        buttons.stream.classList.add('btn-danger');
        buttons.stream.innerText = 'Stop Stream';
    } else {
        buttons.stream.classList.remove('btn-danger');
        buttons.stream.classList.add('btn-success');
        buttons.stream.innerText = 'Start Stream';
    }

    if (state.streaming_and_recording) {
        buttons.stream_record.classList.remove('btn-success');
        buttons.stream_record.classList.add('btn-danger');
        buttons.stream_record.innerText = 'Stop Stream & Record';
    } else {
        buttons.stream_record.classList.remove('btn-danger');
        buttons.stream_record.classList.add('btn-success');
        buttons.stream_record.innerText = 'Start Stream & Record';
    }

    if (state.recording) {
        buttons.record.classList.remove('btn-success');
        buttons.record.classList.add('btn-danger');
        buttons.record.innerText = 'Stop Record';
    } else {
        buttons.record.classList.remove('btn-danger');
        buttons.record.classList.add('btn-success');
        buttons.record.innerText = 'Start Record';
    }

    if (state.file_streaming) {
        buttons.file_stream.classList.remove('btn-success');
        buttons.file_stream.classList.add('btn-danger');
        buttons.file_stream.innerText = 'Stop File Stream';
    } else {
        buttons.file_stream.classList.remove('btn-danger');
        buttons.file_stream.classList.add('btn-success');
        buttons.file_stream.innerText = 'Start File Stream';
    }

    for (const buttonKey in buttons) {
        if (buttonKey !== 'stream_record' && state.streaming_and_recording) {
            buttons[buttonKey].disabled = true;
            recordingActions.forEach(action => action.classList.add('hide'));
        } else if (buttonKey !== 'stream' && state.streaming) {
            buttons[buttonKey].disabled = true;
        } else if (buttonKey !== 'record' && state.recording) {
            buttons[buttonKey].disabled = true;
            recordingActions.forEach(action => action.classList.add('hide'));
            // Add disabled class to ALL inputs
            inputs.forEach(input => {
                input.disabled = true;
                input.classList.add('disabled');
            });
            updateButton.forEach(button => {
                button.disabled = true;
                button.classList.add('disabled');
            });
            selects.forEach(select => {
                select.disabled = true;
                select.classList.add('disabled');
            });

        } else if (buttonKey !== 'file_stream' && state.file_streaming) {
            buttons[buttonKey].disabled = true;
            buttons[buttonKey].classList.add('disabled');
        } else {
            buttons[buttonKey].disabled = false;
            buttons[buttonKey].classList.remove('disabled');
            recordingActions.forEach(action => action.classList.remove('hide'));
            // Remove disabled class from ALL inputs
            inputs.forEach(input => {
                input.disabled = false;
                input.classList.remove('disabled');
            });
            updateButton.forEach(button => {
                button.disabled = false;
                button.classList.remove('disabled');
            });
            selects.forEach(select => {
                select.disabled = false;
                select.classList.remove('disabled');
            });
        }
    }
}

function updateLog() {
    fetch('/get_log')
        .then(response => response.json())
        .then(data => {
            if (data.log) {
                document.getElementById('logTextarea').value = data.log;
                // Scroll to the bottom of the textarea
                logTextarea.scrollTop = logTextarea.scrollHeight;
            } else if (data.error) {
                console.error('Error fetching log:', data.error);
            }
        })
        .catch(error => console.error('Error:', error));
}

// Update the log every 5 seconds
setInterval(updateLog, 5000);

function updateFfmpegLog() {
    fetch('/get_ffmpeg_log')
        .then(response => response.json())
        .then(data => {
            if (data.log) {
                document.getElementById('ffmpeglogTextarea').value = data.log;
                // Scroll to the bottom of the textarea
                ffmpeglogTextarea.scrollTop = ffmpeglogTextarea.scrollHeight;
            } else if (data.error) {
                console.error('Error fetching ffmpeg log:', data.error);
            }
        })
        .catch(error => console.error('Error:', error));
}

// Update the ffmpeg log every 5 seconds
setInterval(updateFfmpegLog, 5000);

function get_sys_info() {
    fetch('/get_sys_info')
        .then(response => response.json())
        .then(data => {
            if (data.info) {
                document.getElementById('systemTextarea').value = data.info;
            } else if (data.error) {
                console.error('Error:', data.error);
            }
        })
        .catch(error => console.error('Error:', error));
}

function fetchDiskUsage() {
    fetch('/get_disk_usage')
        .then(response => response.json())
        .then(data => {
            document.getElementById('disk_filesystem').innerText = `File System: ${data.filesystem}`;
            document.getElementById('disk_size').innerText = `Disk Size: ${data.size}`;
            document.getElementById('disk_used').innerText = `Disk Used: ${data.used}`;
            document.getElementById('disk_available').innerText = `Disk Available: ${data.available}`;
            console.log(data);
        })
        .catch(error => console.error('Error fetching stats:', error));
}

function fetchStats() {
    fetch('/get_cpu_stats')
        .then(response => response.json())
        .then(data => {
            document.getElementById('cpu_usage').innerText = `CPU Usage: ${data.cpu_usage}%`;
            document.getElementById('memory_usage_percent').innerText = `Memory Usage: ${data.memory_usage_percent}%`;
            console.log(data);
        })
        .catch(error => console.error('Error fetching stats:', error));
}

function confirmDelete(directory, filename) {
    if (confirm(`Are you sure you want to delete the file '${filename}' from '${directory}'?`)) {
        fetch('/delete_file', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: `directory=${directory}&filename=${filename}`
        })
            .then(response => response.json())
            .then(data => {
                console.log(data);
                setTimeout(() => {
                    window.location.reload();
                }, 500);
            })
            .catch(error => console.error(error));
    }
}

document.querySelectorAll('.videoButton').forEach(button => {
    button.addEventListener('click', function () {
        let video = document.getElementById('videoElement');
        let videoSource = document.getElementById('videoSource');
        let newSrc = this.getAttribute('data-id');
        let title = document.getElementById('fileName');
        let videoPlayer = document.getElementById('videoPlayer');
        let rowTr = this.closest('tr');

        videoPlayer.classList.remove('hide');

        let activeRows = document.querySelectorAll('.row-active');

        activeRows.forEach(function (row) {
            row.classList.remove('row-active');
        });

        rowTr.classList.add('row-active');

        title.textContent = newSrc;
        videoSource.setAttribute('src', newSrc);
        video.load();
        video.play();
    });
});

setInterval(fetchStats, 5000);
fetchStats(); // Initial call

setInterval(fetchDiskUsage, 5000);
fetchDiskUsage(); // Initial call

document.addEventListener('DOMContentLoaded', function () {
    // Load log data
    updateLog();
    get_sys_info();
});