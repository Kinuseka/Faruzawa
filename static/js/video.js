document.addEventListener('DOMContentLoaded', () => {
	const video = document.getElementById('video-player')
    const source = video.getElementsByTagName("source")[0].src;
    const player = null
    // For more options see: https://github.com/sampotts/plyr/#options
    const defaultOptions = {'storage': { enabled: true, key: 'faruzawa_player' }, 
		'keyboard': {focused: false, global: true},  
		'invertTime': false,
		'displayDuration': true,
		'i18n': {
			'seekLabel': '{currentTime}/{duration}'
		}
	};

	if (!Hls.isSupported()) {
		video.src = source;
		player = new Plyr(video, defaultOptions);
	} else {
		// For more Hls.js options, see https://github.com/dailymotion/hls.js
		const hls = new Hls();
		hls.loadSource(source);

		// From the m3u8 playlist, hls parses the manifest and returns
        // all available video qualities. This is important, in this approach,
        // we will have one source on the Plyr player.
        hls.on(Hls.Events.MANIFEST_PARSED, function (event, data) {
            // Transform available levels into an array of integers (height values).
            const availableQualities = hls.levels.map((l) => l.height).reverse()
	      	availableQualities.unshift(0) //prepend 0 to quality array
	      	// Add new qualities to option
		    defaultOptions.quality = {
		    	default: 0, //Default - AUTO
		        options: availableQualities,
		        forced: true,        
		        onChange: (e) => updateQuality(e),
		    }
		    // Add Auto Label 
			defaultOptions.i18n.qualityLabel = {
				0: 'Auto',
			}
		    hls.on(Hls.Events.LEVEL_SWITCHED, function (event, data) {
	          var span = document.querySelector(".plyr__menu__container [data-plyr='quality'][value='0'] span")
	          if (hls.autoLevelEnabled) {
				  span.innerHTML = `Auto (${hls.levels[data.level].height}p)`
				} else {
					span.innerHTML = `Auto`
				}
	        })
			// Initialize new Plyr player with quality options
			console.log('An error relating to blob://... should be expected after reinitializing player');
            player = new Plyr(video, defaultOptions);
        });	
		
		hls.attachMedia(video);
    	window.hls = hls;		 
    }
	
	video.addEventListener('ready', (event) => {
		console.log('plyr is ready '+ event)
		var fullscreenButton = $('.plyr__controls__item.plyr__control[data-plyr="fullscreen"]');
		fullscreenButton.on('click', function() {
			setTimeout(() => {
				if ($(this).attr('aria-pressed') === 'true') {
					// Entering fullscreen
					handleFullscreenChange();
				} else {
					// Exiting fullscreen
					handleFullscreenChange();
				}
			}, 100); // Timeout to allow aria-pressed to update
		});
	});
	
    
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