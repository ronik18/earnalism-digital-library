/** Only a superseded responsive image is exempt: its exact canonical asset must
 * already be decoded in the current visible cover. All other failures stay fatal. */
export function canonicalCover(url) {
  try {
    const parsed = new URL(url);
    if (parsed.origin !== 'https://res.cloudinary.com') return null;
    const match = parsed.pathname.match(/^\/dzlrhlfpu\/image\/upload\/(?:[^/]+\/)?(v\d+\/earnalism\/covers\/(?:front|back)\/[^/]+)$/);
    return match ? match[1] : null;
  } catch { return null; }
}
export function classifyRecoveryFailures(failures, decodedImages, allowedAssets) {
  const fatal = [], superseded = [];
  for (const failure of failures) {
    const asset = canonicalCover(failure.url);
    const proof = decodedImages.find(image => image.visible && image.complete && image.naturalWidth > 0
      && image.decoded === true && image.currentSrc !== failure.url && canonicalCover(image.currentSrc) === asset);
    if (failure.error === 'net::ERR_ABORTED' && failure.resourceType === 'image'
      && asset && allowedAssets.includes(asset) && proof) superseded.push({ ...failure, decoded_replacement: proof });
    else fatal.push(failure);
  }
  return { fatal, superseded };
}
export async function collectDecodedRecoveryCovers(images) {
  return Promise.all(images.map(async image => {
    const rect = image.getBoundingClientRect();
    const visible = image.isConnected && rect.width > 0 && rect.height > 0 && getComputedStyle(image).visibility !== 'hidden';
    const sourceBeforeDecode = image.currentSrc;
    let decoded = false;
    if (visible) {
      let timer;
      try { await Promise.race([image.decode(), new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('cover decode deadline')), 10000); })]); decoded = image.currentSrc === sourceBeforeDecode; }
      catch { /* A failed decode supplies no replacement proof. */ }
      finally { clearTimeout(timer); }
    }
    const currentRect = image.getBoundingClientRect();
    const currentlyVisible = image.isConnected && currentRect.width > 0 && currentRect.height > 0 && getComputedStyle(image).visibility !== 'hidden';
    return { currentSrc: image.currentSrc, visible: currentlyVisible, complete: image.complete, naturalWidth: image.naturalWidth, decoded };
  }));
}
export async function decodedRecoveryCovers(page) {
  return page.locator('.book-cover-image__img').evaluateAll(collectDecodedRecoveryCovers);
}
