/**
 * src2 watch page: disguised PNG/WebP vault segments → MPEG-TS in the client.
 * No-op for plain TS and for Zen AES ciphertext (see documentation/SRC-2-DECODER.md).
 * Not loaded for src1 (Gogo).
 */
(function (global) {
	'use strict';

	const SEGMENT_XOR_KEY = new Uint8Array([
		157, 42, 241, 71, 179, 142, 92, 112, 166, 25, 228, 59, 216, 98, 15, 197,
	]);

	const PNG_SIG = [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a];

	function isWebpContainer(u8) {
		return (
			u8.length >= 12 &&
			u8[0] === 0x52 &&
			u8[1] === 0x49 &&
			u8[2] === 0x46 &&
			u8[3] === 0x46 &&
			u8[8] === 0x57 &&
			u8[9] === 0x45 &&
			u8[10] === 0x42 &&
			u8[11] === 0x50
		);
	}

	function isPngContainer(u8) {
		if (u8.length < 8) {
			return false;
		}
		for (let i = 0; i < 8; i++) {
			if (u8[i] !== PNG_SIG[i]) {
				return false;
			}
		}
		return true;
	}

	/** Already demux-ready TS (src1-style or post-decode); do not peel/XOR. */
	function isPlainMpegTs(u8) {
		return u8.length >= 376 && u8[0] === 0x47 && u8[188] === 0x47;
	}

	function transformDisguisedSegment(input) {
		const body = input instanceof ArrayBuffer ? new Uint8Array(input) : input;
		if (isPlainMpegTs(body)) {
			return input instanceof ArrayBuffer
				? input
				: body.buffer.slice(body.byteOffset, body.byteOffset + body.byteLength);
		}
		let peeled = null;
		let useXor = true;

		if (isWebpContainer(body)) {
			peeled = body.subarray(12);
			if (body.length >= 13 && body[12] === 0x47) {
				useXor = false;
			}
		} else if (isPngContainer(body)) {
			peeled = body.subarray(8);
			if (body.length >= 9 && body[8] === 0x47) {
				useXor = false;
			}
		} else {
			return input instanceof ArrayBuffer ? input : input.buffer.slice(
				input.byteOffset,
				input.byteOffset + input.byteLength,
			);
		}

		if (!useXor) {
			return new Uint8Array(peeled).buffer;
		}

		const out = new Uint8Array(peeled.length);
		for (let i = 0; i < peeled.length; i++) {
			out[i] = peeled[i] ^ SEGMENT_XOR_KEY[i & 15];
		}
		return out.buffer;
	}

	function toArrayBuffer(data) {
		if (data instanceof ArrayBuffer) {
			return data;
		}
		if (ArrayBuffer.isView(data)) {
			return data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength);
		}
		return data;
	}

	function shouldTransformFragment(context, response) {
		if (!context || context.responseType !== 'arraybuffer') {
			return false;
		}
		if (!response || response.data == null) {
			return false;
		}
		const u8 = new Uint8Array(toArrayBuffer(response.data));
		if (isPlainMpegTs(u8)) {
			return false;
		}
		// src1 (AES ciphertext) and src1-style segments: no PNG/WebP shell — leave bytes for Hls.js / AES.
		return isWebpContainer(u8) || isPngContainer(u8);
	}

	function createHlsConfig(Hls) {
		const BaseLoader = Hls.DefaultConfig.loader;
		class Src2FragmentLoader extends BaseLoader {
			load(context, config, callbacks) {
				const onSuccess = callbacks.onSuccess;
				callbacks.onSuccess = (response, stats, ctx, networkDetails) => {
					if (shouldTransformFragment(ctx, response)) {
						response.data = transformDisguisedSegment(
							toArrayBuffer(response.data),
						);
					}
					onSuccess(response, stats, ctx, networkDetails);
				};
				super.load(context, config, callbacks);
			}
		}
		return { fLoader: Src2FragmentLoader };
	}

	global.FrzwSrc2Decoder = {
		transformDisguisedSegment,
		createHlsConfig,
	};
})(typeof window !== 'undefined' ? window : globalThis);
