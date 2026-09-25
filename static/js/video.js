document.addEventListener('DOMContentLoaded', () => {
	const video = document.getElementById('video-player')
    const source = video.getElementsByTagName("source")[0].src;
    let player = null
    let networkRecoveries = 0;
    let mediaRecoveries = 0;
    const MAX_NETWORK_RECOVERIES = 2;
    const MAX_MEDIA_RECOVERIES = 2;

    // For more options see: https://github.com/sampotts/plyr/#options
    const defaultOptions = {'storage': { enabled: true, key: 'faruzawa_player' },
		'keyboard': {focused: false, global: true},
		'invertTime': false,
		'displayDuration': true,
		'i18n': {
			'seekLabel': '{currentTime}/{duration}'
		}
	};

	function initPlyr(options) {
		if (player) {
			return player;
		}
		player = new Plyr(video, options);
		bindFullscreenHandler();
		return player;
	}

	function bindFullscreenHandler() {
		if (!player || typeof $ === 'undefined') {
			return;
		}
		player.on('ready', () => {
			const fullscreenButton = $('.plyr__controls__item.plyr__control[data-plyr="fullscreen"]');
            if (!fullscreenButton || !fullscreenButton.on) {
                return;
            }
			fullscreenButton.on('click', function () {
				setTimeout(() => {
					handleFullscreenChange();
				}, 100);
			});
		});
	}

    function showTerminalError(message) {
        console.error('[FRZW-HLS] terminal error:', message);
        const container = document.querySelector('.video-container');
        if (!container) {
            return;
        }
        const overlay = document.createElement('div');
        overlay.className = 'frzw-player-error';
        overlay.style.position = 'absolute';
        overlay.style.inset = '0';
        overlay.style.zIndex = '99';
        overlay.style.background = 'rgba(0, 0, 0, 0.78)';
        overlay.style.display = 'flex';
        overlay.style.alignItems = 'center';
        overlay.style.justifyContent = 'center';
        overlay.style.padding = '1rem';
        overlay.style.textAlign = 'center';
        overlay.style.color = '#fff';
        overlay.style.fontSize = '0.95rem';
        overlay.style.lineHeight = '1.5';
        overlay.textContent = message;
        const existing = container.querySelector('.frzw-player-error');
        if (existing) {
            existing.remove();
        }
        container.appendChild(overlay);
    }

	if (!Hls.isSupported()) {
		video.src = source;
		initPlyr(defaultOptions);
	} else {
		// Segment loading is Hls.js, not Plyr. maxBufferLength is the preload/ahead target in seconds.
		const hls = new Hls({
			maxBufferLength: 30,
			maxMaxBufferLength: 60,
			maxBufferSize: 80 * 1000 * 1000,
			startFragPrefetch: true,
		});

		function plyrOptionsFromLevels() {
			const options = {
				...defaultOptions,
				i18n: { ...defaultOptions.i18n },
			};
			const heights = hls.levels.map((l) => l.height).filter(Boolean);
			if (heights.length > 1) {
				const availableQualities = heights.slice().reverse();
				availableQualities.unshift(0);
				options.quality = {
					default: 0,
					options: availableQualities,
					forced: true,
					onChange: (e) => updateQuality(e),
				};
				options.i18n.qualityLabel = { 0: 'Auto' };
			}
			return options;
		}

		hls.on(Hls.Events.MANIFEST_PARSED, function () {
			initPlyr(plyrOptionsFromLevels());
			hls.on(Hls.Events.LEVEL_SWITCHED, function (event, data) {
				const span = document.querySelector(".plyr__menu__container [data-plyr='quality'][value='0'] span");
				if (!span || !hls.levels[data.level]) {
					return;
				}
				if (hls.autoLevelEnabled) {
					span.innerHTML = `Auto (${hls.levels[data.level].height}p)`;
				} else {
					span.innerHTML = 'Auto';
				}
			});
		});

        hls.on(Hls.Events.MEDIA_ATTACHED, () => {
            hls.loadSource(source);
        });
		hls.on(Hls.Events.ERROR, function (event, data) {
            const statusCode = data && data.response ? data.response.code : null;
			if (!data.fatal) {
				return;
			}
			switch (data.type) {
				case Hls.ErrorTypes.NETWORK_ERROR:
                    if (statusCode === 401 || statusCode === 403) {
                        showTerminalError(`Stream rejected by upstream (HTTP ${statusCode}).`);
                        return;
                    }
                    networkRecoveries += 1;
                    if (networkRecoveries > MAX_NETWORK_RECOVERIES) {
                        showTerminalError('Playback stopped after repeated network recovery failures.');
                        return;
                    }
                    setTimeout(() => hls.startLoad(video.currentTime), 250);
					break;
				case Hls.ErrorTypes.MEDIA_ERROR:
                    mediaRecoveries += 1;
                    if (mediaRecoveries > MAX_MEDIA_RECOVERIES) {
                        showTerminalError('Playback stopped after repeated media recovery failures.');
                        return;
                    }
                    setTimeout(() => hls.recoverMediaError(), 250);
					break;
				default:
                    showTerminalError('Playback stopped due to an unrecoverable stream error.');
					break;
			}
		});

		hls.attachMedia(video);
    	window.hls = hls;
    }
	
    
	function updateQuality(newQuality) {
      if (newQuality === 0) {
        window.hls.currentLevel = -1; //Enable AUTO quality if option.value = 0
      } else {
        window.hls.levels.forEach((level, levelIndex) => {
          if (level.height === newQuality) {
            console.log("Found quality match with " + newQuality);
            window.hls.currentLevel = levelIndex;
          }
        });
      }
    }
	function handleFullscreenChange(event) {
		if (document.fullscreenElement || document.webkitFullscreenElement || document.mozFullScreenElement || document.msFullscreenElement) {
		  // Entered fullscreen
		  	if (screen.orientation && screen.orientation.lock) {
			screen.orientation.lock('landscape').catch((err) => {
				if (err.name === 'NotSupportedError') {
					console.warn('Screen orientation lock not supported.');
				} else {
					console.error('Failed to lock orientation: ', err);
				}
			});
			} else {
				console.warn('Screen orientation lock not supported.');
			}
		} else {
			// Exited fullscreen
			if (screen.orientation && screen.orientation.unlock) {
				screen.orientation.unlock()
			} else {
				console.warn('Screen orientation lock not supported.');
			}
			}
	  }
    
});
