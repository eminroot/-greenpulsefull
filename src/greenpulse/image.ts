import * as ImageManipulator from 'expo-image-manipulator';

export interface ProcessedImage {
  uri: string;
}

// Downscale and compress a leaf photo before it is uploaded. Greenhouse wifi is
// often poor, and the node does not need a full resolution frame to score a
// leaf. Resizing is an optimisation only: on any failure the original uri is
// returned unchanged and the upload still works.
export async function compressLeafImage(uri: string, maxWidth = 768): Promise<ProcessedImage> {
  try {
    const fn = (ImageManipulator as { manipulateAsync?: typeof ImageManipulator.manipulateAsync })
      .manipulateAsync;
    if (typeof fn === 'function') {
      const out = await fn(uri, [{ resize: { width: maxWidth } }], {
        compress: 0.6,
        format: ImageManipulator.SaveFormat.JPEG,
      });
      return { uri: out.uri };
    }
    return { uri };
  } catch {
    return { uri };
  }
}
