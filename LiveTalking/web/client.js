var pc = null;
var _connected = false;

function negotiate() {
    pc.addTransceiver('video', { direction: 'recvonly' });
    pc.addTransceiver('audio', { direction: 'recvonly' });
    return pc.createOffer().then((offer) => {
        return pc.setLocalDescription(offer);
    }).then(() => {
        // wait for ICE gathering to complete (with 5s timeout)
        return new Promise((resolve) => {
            if (pc.iceGatheringState === 'complete') {
                resolve();
            } else {
                var timeout = setTimeout(resolve, 5000);
                var checkState = function() {
                    if (pc.iceGatheringState === 'complete') {
                        clearTimeout(timeout);
                        pc.removeEventListener('icegatheringstatechange', checkState);
                        resolve();
                    }
                };
                pc.addEventListener('icegatheringstatechange', checkState);
            }
        });
    }).then(() => {
        var offer = pc.localDescription;
        return fetch('/offer', {
            body: JSON.stringify({
                sdp: offer.sdp,
                type: offer.type,
            }),
            headers: {
                'Content-Type': 'application/json'
            },
            method: 'POST'
        });
    }).then((response) => {
        return response.json();
    }).then((answer) => {
        document.getElementById('sessionid').value = answer.sessionid;
        return pc.setRemoteDescription(answer);
    }).catch((e) => {
        console.error('Negotiation failed:', e);
    });
}

function start() {
    var config = {
        sdpSemantics: 'unified-plan',
        iceServers: [{ urls: ['stun:stun.l.google.com:19302'] }]
    };

    if (document.getElementById('use-stun').checked) {
        config.iceServers = [
            { urls: ['stun:stun.l.google.com:19302'] },
            { urls: ['stun:stun1.l.google.com:19302'] }
        ];
    }

    pc = new RTCPeerConnection(config);

    // Monitor connection state for auto-recovery
    pc.addEventListener('connectionstatechange', function() {
        console.log('Connection state:', pc.connectionState);
        if (pc.connectionState === 'connected') {
            _connected = true;
        }
        if (pc.connectionState === 'failed' && _connected) {
            console.warn('Connection failed, attempting reconnect...');
            _connected = false;
            stop();
            setTimeout(start, 1500);
        }
    });

    // Connect audio / video with low-latency settings
    pc.addEventListener('track', function(evt) {
        if (evt.track.kind === 'video') {
            document.getElementById('video').srcObject = evt.streams[0];
            // Request low-latency jitter buffer
            try {
                var receiver = evt.receiver;
                if (receiver && receiver.jitterBufferTarget !== undefined) {
                    receiver.jitterBufferTarget = 0;
                }
            } catch(e) { /* not supported */ }
        } else {
            document.getElementById('audio').srcObject = evt.streams[0];
            try {
                var receiver = evt.receiver;
                if (receiver && receiver.jitterBufferTarget !== undefined) {
                    receiver.jitterBufferTarget = 0;
                }
            } catch(e) { /* not supported */ }
        }
    });

    document.getElementById('start').style.display = 'none';
    negotiate();
    document.getElementById('stop').style.display = 'inline-block';
}

function stop() {
    document.getElementById('stop').style.display = 'none';
    _connected = false;
    if (pc) {
        pc.close();
        pc = null;
    }
}

// Clean close on page unload (non-blocking)
window.addEventListener('beforeunload', function() {
    if (pc) {
        pc.close();
        pc = null;
    }
});