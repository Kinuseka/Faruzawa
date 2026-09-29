document.addEventListener('DOMContentLoaded', () => {
	if (new URLSearchParams(window.location.search).get('hlsDebug') === '1') {
		try {
			localStorage.setItem('debug', 'hls:*');
		} catch (_) {
			// ignore
		}
	}

	const video = document.getElementById('video-player');
	const trackControls = document.getElementById('frzw-track-controls');
	const initialMaster =
		video.dataset.masterUrl || video.getElementsByTagName('source')[0]?.src || '';
	let currentMaster = initialMaster;
	let playbackMeta = null;
	let player = null;
	let jassubInstance = null;
	let jassubResizeBound = false;
	let plyrCaptionSyncBound = false;
	let captionAppliedValue = null;
	let captionUserOverride = false;

	const JASSUB_ASSETS = '/static/js/jassub';
	const JASSUB_FALLBACK_WOFF2 = `${JASSUB_ASSETS}/default.woff2`;

	function jassubFontConfig() {
		// One bundled Liberation Sans file; map common ASS Fontname values to it.
		const url = JASSUB_FALLBACK_WOFF2;
		const names = [
			'liberation sans',
			'arial',
			'trebuchet ms',
			'comic sans ms',
			'ubuntu',
			'roboto',
			'verdana',
			'tahoma',
			'Segoe UI',
		];
		const availableFonts = {};
		names.forEach((name) => {
			availableFonts[name.toLowerCase()] = url;
		});
		return {
			availableFonts,
			fallbackFont: 'liberation sans',
			// Avoid Local Font Access mismatches; ASS styles use the map above.
			useLocalFonts: false,
		};
	}
    let networkRecoveries = 0;
    let mediaRecoveries = 0;
    const MAX_NETWORK_RECOVERIES = 2;
    const MAX_MEDIA_RECOVERIES = 2;

	const defaultOptions = {
		storage: { enabled: true, key: 'faruzawa_player' },
		keyboard: { focused: false, global: true },
		invertTime: false,
		displayDuration: true,
		// Plyr captions menu: WebVTT <track> elements only (SRT is converted to VTT on the server).
		captions: { active: false, update: true, language: 'auto' },
		i18n: {
			seekLabel: '{currentTime}/{duration}',
		},
	};

	function initPlyr(options) {
		if (player) {
			return player;
		}
		player = new Plyr(video, options);
		bindFullscreenHandler();
		bindPlyrCaptionSync();
		return player;
	}

	function bindFullscreenHandler() {
		if (!player || typeof $ === 'undefined') {
			return;
		}
		player.on('ready', () => {
			const fullscreenButton = $(
				'.plyr__controls__item.plyr__control[data-plyr="fullscreen"]'
			);
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

	function hidePlayerLoading() {
		const loading = document.getElementById('frzw-player-loading');
		if (!loading || loading.hidden) {
			return;
		}
		loading.hidden = true;
		loading.removeAttribute('aria-busy');
	}

	function bindPlayerLoadingDismiss() {
		video.addEventListener(
			'canplay',
			() => {
				hidePlayerLoading();
			},
			{ once: true }
		);
	}

	function showTerminalError(message) {
		console.error('[FRZW-HLS] terminal error:', message);
		hidePlayerLoading();
		const panel = document.getElementById('frzw-player-error');
		const text = document.getElementById('frzw-player-error-text');
		if (!panel) {
			return;
		}
		if (text) {
			text.textContent = message || '';
			text.hidden = !message;
		}
		panel.hidden = false;
	}

	function clearTrackControls() {
		if (!trackControls) {
			return;
		}
		trackControls.innerHTML = '';
		trackControls.hidden = true;
	}

	function addTrackGroup(labelText, selectEl) {
		if (!trackControls) {
			return;
		}
		const wrap = document.createElement('label');
		wrap.className = 'frzw-track-control';
		const span = document.createElement('span');
		span.textContent = labelText;
		wrap.appendChild(span);
		wrap.appendChild(selectEl);
		trackControls.appendChild(wrap);
		trackControls.hidden = false;
	}

	function scheduleJassubResize() {
		if (!jassubInstance || typeof jassubInstance.resize !== 'function') {
			return;
		}
		requestAnimationFrame(() => {
			if (jassubInstance && typeof jassubInstance.resize === 'function') {
				jassubInstance.resize();
			}
		});
	}

	function onJassubLayoutChange() {
		scheduleJassubResize();
	}

	function bindJassubLayoutListeners() {
		if (jassubResizeBound) {
			return;
		}
		jassubResizeBound = true;
		window.addEventListener('resize', onJassubLayoutChange);
		document.addEventListener('fullscreenchange', onJassubLayoutChange);
		document.addEventListener('webkitfullscreenchange', onJassubLayoutChange);
		if (player) {
			player.on('enterfullscreen', onJassubLayoutChange);
			player.on('exitfullscreen', onJassubLayoutChange);
			player.on('ready', onJassubLayoutChange);
		}
	}

	function unbindJassubLayoutListeners() {
		if (!jassubResizeBound) {
			return;
		}
		jassubResizeBound = false;
		window.removeEventListener('resize', onJassubLayoutChange);
		document.removeEventListener('fullscreenchange', onJassubLayoutChange);
		document.removeEventListener('webkitfullscreenchange', onJassubLayoutChange);
		if (player) {
			player.off('enterfullscreen', onJassubLayoutChange);
			player.off('exitfullscreen', onJassubLayoutChange);
		}
	}

	function setAssRendering(active) {
		const root = video.closest('.plyr');
		if (root) {
			root.classList.toggle('plyr--frzw-ass', active);
		}
	}

	function hideAllTextTracks() {
		for (let i = 0; i < video.textTracks.length; i += 1) {
			const textTrack = video.textTracks[i];
			if (textTrack.kind === 'captions' || textTrack.kind === 'subtitles') {
				textTrack.mode = 'hidden';
			}
		}
	}

	function syncCaptionSelectValue(value) {
		const select = trackControls?.querySelector('[aria-label="Captions"]');
		if (select && select.value !== value) {
			select.value = value;
		}
	}

	function destroyJassub() {
		unbindJassubLayoutListeners();
		if (jassubInstance && typeof jassubInstance.destroy === 'function') {
			jassubInstance.destroy();
		}
		jassubInstance = null;
		setAssRendering(false);
	}

	function clearNativeCaptionTracks() {
		video.querySelectorAll('track[data-frzw-caption]').forEach((node) => node.remove());
	}

	function externalTracksFromMeta(meta) {
		return ((meta && meta.subtitles) || []).filter(
			(row) => row.source === 'external' && row.url
		);
	}

	function externalTracksForUi(meta) {
		const rank = (track) => {
			const kind = trackKind(track);
			if (kind === 'ass' || kind === 'ssa') {
				return 0;
			}
			if (kind === 'srt' || kind === 'vtt') {
				return 1;
			}
			return 2;
		};
		return externalTracksFromMeta(meta)
			.slice()
			.sort((a, b) => rank(a) - rank(b) || (a.label || '').localeCompare(b.label || ''));
	}

	function captionOptionLabel(track) {
		const base = track.label || track.language || 'Subtitles';
		const kind = trackKind(track);
		if (kind === 'ass' || kind === 'ssa') {
			return `${base} (ASS)`;
		}
		if (kind === 'srt') {
			return `${base} (CC)`;
		}
		return base;
	}

	function normalizeSrclang(lang) {
		if (!lang) {
			return 'en';
		}
		const value = String(lang).toLowerCase();
		if (value === 'eng') {
			return 'en';
		}
		if (value.length >= 2) {
			return value.slice(0, 2);
		}
		return value;
	}

	// playback.json subtitles — ids are usually "{code}-{label}" (e.g. eng-English…, en-Dubtitle…)
	const ENGLISH_SUBTITLE_RE = /english|\ben\b|\beng\b/i;

	function playbackSubtitleLooksEnglish(track) {
		if (!track) {
			return false;
		}
		const id = String(track.id || '');
		const language = String(track.language || track.lang || '')
			.trim()
			.toLowerCase();
		const label = String(track.label || '');
		if (/^(eng|en)([-_.]|$)/i.test(id)) {
			return true;
		}
		if (id && ENGLISH_SUBTITLE_RE.test(id)) {
			return true;
		}
		if (
			language === 'english' ||
			/^(eng|en)([-_.]|$)/.test(language) ||
			/^en[-_]/.test(language)
		) {
			return true;
		}
		if (ENGLISH_SUBTITLE_RE.test(label)) {
			return true;
		}
		if (/\((eng|english)\)|\[(eng|english)\]/i.test(label)) {
			return true;
		}
		return ENGLISH_SUBTITLE_RE.test(`${id} ${language} ${label}`);
	}

	function hlsSubtitleTrackLooksEnglish(track) {
		if (!track) {
			return false;
		}
		const name = String(track.name || '');
		const lang = String(track.lang || '').trim().toLowerCase();
		if (ENGLISH_SUBTITLE_RE.test(name)) {
			return true;
		}
		if (/^(eng|en)([-_.]|$)/.test(lang) || lang === 'english' || /^en[-_]/.test(lang)) {
			return true;
		}
		return ENGLISH_SUBTITLE_RE.test(`${name} ${lang}`);
	}

	function externalIndexForPlaybackTrack(external, track) {
		if (!track) {
			return -1;
		}
		if (track.id) {
			const byId = external.findIndex((row) => row.id === track.id);
			if (byId >= 0) {
				return byId;
			}
		}
		return external.indexOf(track);
	}

	function pickDefaultEnglishCaptionValue(hls, external, meta) {
		const fromPlayback = ((meta && meta.subtitles) || []).filter(
			(row) => row.source === 'external' && row.url
		);
		let chosen = null;
		for (const row of fromPlayback) {
			if (!playbackSubtitleLooksEnglish(row)) {
				continue;
			}
			chosen = row;
			const kind = trackKind(row);
			if (kind === 'ass' || kind === 'ssa') {
				break;
			}
		}
		if (!chosen) {
			for (const row of fromPlayback) {
				if (playbackSubtitleLooksEnglish(row)) {
					chosen = row;
					break;
				}
			}
		}
		if (chosen) {
			const idx = externalIndexForPlaybackTrack(external, chosen);
			if (idx >= 0) {
				return `ext:${idx}`;
			}
		}
		for (let i = 0; i < external.length; i += 1) {
			if (playbackSubtitleLooksEnglish(external[i])) {
				return `ext:${i}`;
			}
		}
		const hlsTracks = (hls && hls.subtitleTracks) || [];
		for (let i = 0; i < hlsTracks.length; i += 1) {
			if (hlsSubtitleTrackLooksEnglish(hlsTracks[i])) {
				return `hls:${i}`;
			}
		}
		return null;
	}

	function applyDefaultCaptionSelection(chosen, hls, external) {
		if (!chosen || chosen === 'off') {
			return;
		}
		applyCaptionSelection(chosen, hls, external);
	}

	function captionOptionExists(select, value) {
		return Boolean(select.querySelector(`option[value="${CSS.escape(value)}"]`));
	}

	function resolveCaptionSelectValue(select, hls, external, meta) {
		if (captionUserOverride && captionAppliedValue === 'off') {
			return 'off';
		}
		if (
			captionAppliedValue &&
			captionAppliedValue !== 'off' &&
			captionOptionExists(select, captionAppliedValue)
		) {
			return captionAppliedValue;
		}
		return pickDefaultEnglishCaptionValue(hls, external, meta);
	}

	function trackKind(track) {
		const kind = (track.kind || '').toLowerCase();
		if (kind) {
			return kind;
		}
		const path = (track.url || '').split('?')[0].toLowerCase();
		if (path.endsWith('.ass') || path.endsWith('.ssa')) {
			return 'ass';
		}
		if (path.endsWith('.srt')) {
			return 'srt';
		}
		if (path.endsWith('.vtt')) {
			return 'vtt';
		}
		return 'vtt';
	}

	function isPlyrCaptionTrack(track) {
		const kind = trackKind(track);
		return kind === 'srt' || kind === 'vtt';
	}

	function hasWebVttCaptionSources(meta, hls) {
		const externalWeb = externalTracksFromMeta(meta).some(isPlyrCaptionTrack);
		const hlsSubs = Boolean(hls && hls.subtitleTracks && hls.subtitleTracks.length);
		return externalWeb || hlsSubs;
	}

	function plyrControlsForPlayback(meta, hls) {
		const controls = [
			'play-large',
			'play',
			'progress',
			'current-time',
			'mute',
			'volume',
			'captions',
			'settings',
			'pip',
			'airplay',
			'fullscreen',
		];
		if (!hasWebVttCaptionSources(meta, hls)) {
			return controls.filter((item) => item !== 'captions');
		}
		return controls;
	}

	function bindPlyrCaptionSync() {
		if (!player || plyrCaptionSyncBound) {
			return;
		}
		plyrCaptionSyncBound = true;
		player.on('captionsenabled', () => {
			if (jassubInstance) {
				destroyJassub();
			}
			syncCaptionSelectValue('off');
		});
		player.on('languagechange', () => {
			if (jassubInstance) {
				destroyJassub();
				syncCaptionSelectValue('off');
			}
		});
		player.on('ready', () => {
			scheduleJassubResize();
		});
		video.addEventListener('loadedmetadata', scheduleJassubResize);
	}

	function vttPlaybackUrl(track) {
		const kind = trackKind(track);
		if (kind === 'srt') {
			const sep = track.url.includes('?') ? '&' : '?';
			return `${track.url}${sep}format=vtt`;
		}
		return track.url;
	}

	function plyrCaptionsOn() {
		return Boolean(player?.captions?.toggled);
	}

	function setPlyrCaptionsEnabled(enabled) {
		if (!player || typeof player.toggleCaptions !== 'function') {
			return;
		}
		const wantOn = Boolean(enabled);
		if (wantOn && !plyrCaptionsOn()) {
			player.toggleCaptions(true);
		} else if (!wantOn && plyrCaptionsOn()) {
			player.toggleCaptions(false);
		}
	}

	function refreshPlyrCaptions() {
		if (!player || !player.config?.captions?.update) {
			return;
		}
		try {
			video.textTracks.dispatchEvent(new Event('addtrack'));
		} catch (_) {
			// Plyr rescans tracks on addtrack when captions.update is true
		}
	}

	function showPlyrCaptionTrack(trackMeta) {
		const label = trackMeta.label || 'Captions';
		const lang = normalizeSrclang(trackMeta.language);
		let matched = false;
		for (let i = 0; i < video.textTracks.length; i += 1) {
			const textTrack = video.textTracks[i];
			if (textTrack.kind !== 'captions' && textTrack.kind !== 'subtitles') {
				continue;
			}
			const isMatch =
				textTrack.label === label ||
				(textTrack.language && textTrack.language.startsWith(lang));
			textTrack.mode = isMatch ? 'showing' : 'hidden';
			if (isMatch) {
				matched = true;
			}
		}
		if (matched) {
			refreshPlyrCaptions();
			setPlyrCaptionsEnabled(true);
		}
		return matched;
	}

	function installWebVttCaptionTracks(meta) {
		clearNativeCaptionTracks();
		const webTracks = externalTracksFromMeta(meta).filter(isPlyrCaptionTrack);
		webTracks.forEach((track, index) => {
			const tr = document.createElement('track');
			tr.kind = 'captions';
			tr.label = track.label || track.language || `Captions ${index + 1}`;
			tr.srclang = normalizeSrclang(track.language);
			tr.src = vttPlaybackUrl(track);
			tr.setAttribute('data-frzw-caption', '1');
			tr.setAttribute('data-frzw-caption-label', tr.label);
			tr.addEventListener('load', refreshPlyrCaptions);
			video.appendChild(tr);
		});
		return webTracks.length;
	}

	function applyExternalSubtitle(track) {
		destroyJassub();
		if (window.hls) {
			window.hls.subtitleTrack = -1;
		}
		if (!track) {
			setPlyrCaptionsEnabled(false);
			return;
		}
		const kind = trackKind(track);
		if (kind === 'ass' || kind === 'ssa') {
			if (!globalThis.JASSUB) {
				console.warn(
					'[FRZW-HLS] ASS subtitles need JASSUB; pick an SRT track for Plyr CC instead'
				);
				return;
			}
			hideAllTextTracks();
			setPlyrCaptionsEnabled(false);
			setAssRendering(true);
			jassubInstance = new JASSUB({
				video,
				subUrl: track.url,
				workerUrl: `${JASSUB_ASSETS}/jassub-worker.js`,
				wasmUrl: `${JASSUB_ASSETS}/jassub-worker.wasm`,
				...jassubFontConfig(),
			});
			jassubInstance.addEventListener('ready', scheduleJassubResize);
			jassubInstance.addEventListener('error', (event) => {
				console.warn('[FRZW-HLS] JASSUB error', event.error || event);
			});
			bindJassubLayoutListeners();
			scheduleJassubResize();
			return;
		}
		setAssRendering(false);
		if (!isPlyrCaptionTrack(track)) {
			return;
		}
		if (showPlyrCaptionTrack(track)) {
			return;
		}
		const tr = document.createElement('track');
		tr.kind = 'captions';
		tr.label = track.label || 'Captions';
		tr.srclang = normalizeSrclang(track.language);
		tr.src = vttPlaybackUrl(track);
		tr.default = true;
		tr.setAttribute('data-frzw-caption', '1');
		const onReady = () => {
			tr.removeEventListener('load', onReady);
			tr.removeEventListener('error', onError);
			showPlyrCaptionTrack(track);
		};
		const onError = () => {
			tr.removeEventListener('load', onReady);
			tr.removeEventListener('error', onError);
			console.warn('[FRZW-HLS] caption track failed to load', tr.src);
		};
		tr.addEventListener('load', onReady);
		tr.addEventListener('error', onError);
		video.appendChild(tr);
	}

	function removeHlsAudioControl() {
		trackControls
			?.querySelector('[aria-label="Audio"]')
			?.closest('.frzw-track-control')
			?.remove();
	}

	function renderHlsAudioControls(hls) {
		if (!hls.audioTracks || hls.audioTracks.length < 2) {
			return;
		}
		removeHlsAudioControl();
		const select = document.createElement('select');
		select.className = 'frzw-track-select';
		select.setAttribute('aria-label', 'Audio');
		hls.audioTracks.forEach((track, index) => {
			const opt = document.createElement('option');
			opt.value = String(index);
			opt.textContent = track.name || track.lang || `Track ${index + 1}`;
			if (index === hls.audioTrack) {
				opt.selected = true;
			}
			select.appendChild(opt);
		});
		select.addEventListener('change', () => {
			const idx = parseInt(select.value, 10);
			if (!Number.isNaN(idx)) {
				hls.audioTrack = idx;
			}
		});
		addTrackGroup('Audio', select);
	}

	function applyCaptionSelection(value, hls, external) {
		if (value === 'off') {
			destroyJassub();
			for (let i = 0; i < video.textTracks.length; i += 1) {
				const textTrack = video.textTracks[i];
				if (textTrack.kind === 'captions' || textTrack.kind === 'subtitles') {
					textTrack.mode = 'hidden';
				}
			}
			setPlyrCaptionsEnabled(false);
			if (hls) {
				hls.subtitleTrack = -1;
			}
			return;
		}
		if (value.startsWith('hls:')) {
			destroyJassub();
			clearNativeCaptionTracks();
			const idx = parseInt(value.slice(4), 10);
			if (hls && !Number.isNaN(idx)) {
				hls.subtitleTrack = idx;
			}
			return;
		}
		if (value.startsWith('ext:')) {
			const idx = parseInt(value.slice(4), 10);
			const track = external[idx];
			if (track) {
				if (hls) {
					hls.subtitleTrack = -1;
				}
				applyExternalSubtitle(track);
			}
		}
	}

	function renderCaptionControls(hls, meta) {
		const external = externalTracksForUi(meta);
		const hlsTracks = (hls && hls.subtitleTracks) || [];
		if (!external.length && !hlsTracks.length) {
			return;
		}
		const select = document.createElement('select');
		select.className = 'frzw-track-select';
		select.setAttribute('aria-label', 'Captions');
		const off = document.createElement('option');
		off.value = 'off';
		off.textContent = 'Off';
		select.appendChild(off);

		hlsTracks.forEach((track, index) => {
			const opt = document.createElement('option');
			opt.value = `hls:${index}`;
			opt.textContent = track.name || track.lang || `Captions ${index + 1}`;
			select.appendChild(opt);
		});

		external.forEach((track, index) => {
			const opt = document.createElement('option');
			opt.value = `ext:${index}`;
			opt.textContent = captionOptionLabel(track);
			select.appendChild(opt);
		});

		select.addEventListener('change', () => {
			captionUserOverride = true;
			captionAppliedValue = select.value;
			applyCaptionSelection(select.value, hls, external);
		});

		const chosen = resolveCaptionSelectValue(select, hls, external, meta);
		if (chosen && captionOptionExists(select, chosen)) {
			select.value = chosen;
			captionAppliedValue = chosen;
			applyDefaultCaptionSelection(chosen, hls, external);
		} else {
			select.value = 'off';
			if (!captionUserOverride) {
				captionAppliedValue = null;
			} else {
				captionAppliedValue = 'off';
			}
		}

		addTrackGroup('Captions', select);
	}

	async function loadPlaybackMeta() {
		const url = video.dataset.playbackJson;
		if (!url) {
			return null;
		}
		try {
			const resp = await fetch(url, { credentials: 'same-origin' });
			if (!resp.ok) {
				return null;
			}
			return await resp.json();
		} catch (err) {
			console.warn('[FRZW-HLS] playback.json failed', err);
			return null;
		}
	}

	function plyrOptionsFromLevels(hls) {
			const options = {
				...defaultOptions,
				i18n: { ...defaultOptions.i18n },
			controls: plyrControlsForPlayback(playbackMeta, hls),
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

	function updateQuality(newQuality) {
		if (!window.hls) {
			return;
		}
		if (newQuality === 0) {
			window.hls.currentLevel = -1;
		} else {
			window.hls.levels.forEach((level, levelIndex) => {
				if (level.height === newQuality) {
					window.hls.currentLevel = levelIndex;
				}
			});
		}
	}

	function handleFullscreenChange() {
		if (
			document.fullscreenElement ||
			document.webkitFullscreenElement ||
			document.mozFullScreenElement ||
			document.msFullscreenElement
		) {
			if (screen.orientation && screen.orientation.lock) {
				screen.orientation.lock('landscape').catch((err) => {
					if (err.name === 'NotSupportedError') {
						console.warn('Screen orientation lock not supported.');
					} else {
						console.error('Failed to lock orientation: ', err);
					}
				});
			}
		} else if (screen.orientation && screen.orientation.unlock) {
			screen.orientation.unlock();
		}
		scheduleJassubResize();
	}

	function wireHls(hls) {
		let initialSourceLoaded = false;

		hls.on(Hls.Events.LEVEL_SWITCHED, function (event, data) {
			const span = document.querySelector(
				".plyr__menu__container [data-plyr='quality'][value='0'] span"
			);
			if (!span || !hls.levels[data.level]) {
				return;
			}
			if (hls.autoLevelEnabled) {
				span.innerHTML = `Auto (${hls.levels[data.level].height}p)`;
			} else {
				span.innerHTML = 'Auto';
			}
		});

		hls.on(Hls.Events.MANIFEST_PARSED, function () {
			installWebVttCaptionTracks(playbackMeta);
			initPlyr(plyrOptionsFromLevels(hls));
			refreshPlyrCaptions();
			clearTrackControls();
			renderHlsAudioControls(hls);
			renderCaptionControls(hls, playbackMeta);
		});

		hls.on(Hls.Events.AUDIO_TRACKS_UPDATED, function () {
			renderHlsAudioControls(hls);
		});

		hls.on(Hls.Events.SUBTITLE_TRACKS_UPDATED, function () {
			const existing = trackControls?.querySelector('[aria-label="Captions"]');
			if (captionUserOverride && existing?.value) {
				captionAppliedValue = existing.value;
			} else if (!captionUserOverride) {
				captionAppliedValue = null;
			}
			existing?.closest('.frzw-track-control')?.remove();
			renderCaptionControls(hls, playbackMeta);
		});

		hls.on(Hls.Events.MEDIA_ATTACHED, () => {
			if (initialSourceLoaded || !currentMaster) {
				return;
			}
			initialSourceLoaded = true;
			hls.loadSource(currentMaster);
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
	
	bindPlayerLoadingDismiss();

	loadPlaybackMeta().then((meta) => {
		playbackMeta = meta;

		if (!Hls.isSupported()) {
			video.src = currentMaster;
			installWebVttCaptionTracks(playbackMeta);
			initPlyr({
				...defaultOptions,
				controls: plyrControlsForPlayback(playbackMeta, null),
			});
			refreshPlyrCaptions();
			renderCaptionControls(null, playbackMeta);
			return;
		}

		const streamProvider = document.querySelector('.video-container')?.dataset?.streamProvider;
		const hlsOptions = {
			maxBufferLength: 30,
			maxMaxBufferLength: 60,
			maxBufferSize: 80 * 1000 * 1000,
			startFragPrefetch: false,
			testBandwidth: false,
			enableWebVTT: true,
			renderTextTracksNatively: true,
		};
		if (streamProvider === 'src2' && globalThis.FrzwSrc2Decoder) {
			Object.assign(hlsOptions, globalThis.FrzwSrc2Decoder.createHlsConfig(Hls));
		}
		const hls = new Hls(hlsOptions);
		wireHls(hls);
	});
});
