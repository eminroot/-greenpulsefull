import { useEffect, useState } from 'react';
import { Leaf } from 'lucide-react';
import { fetchImageUrl } from '../api/client';

interface Props {
  /** The capture's image_url from the server, or null when it has no photo. */
  path: string | null;
  alt: string;
  className?: string;
  style?: React.CSSProperties;
  /** Icon size for the placeholder shown when there is no photo. */
  fallbackIcon?: number;
}

/**
 * A leaf photo held on the server.
 *
 * Photos are behind the same authentication as everything else, and a plain
 * <img src> sends no Authorization header, so the bytes are fetched with the
 * token and handed to the browser as an object url.
 */
export function AuthImage({ path, alt, className, style, fallbackIcon = 34 }: Props) {
  const [src, setSrc] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!path) {
      setSrc(null);
      return;
    }
    let cancelled = false;
    setFailed(false);

    fetchImageUrl(path)
      .then((url) => {
        if (!cancelled) setSrc(url);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });

    return () => {
      cancelled = true;
    };
  }, [path]);

  if (!path || failed) {
    return (
      <div className={`${className ?? ''} photo-empty`} style={style}>
        <Leaf size={fallbackIcon} />
      </div>
    );
  }

  if (!src) {
    // Hold the layout while the bytes arrive, so a gallery does not jump.
    return <div className={`${className ?? ''} photo-empty`} style={style} />;
  }

  return <img className={className} style={style} src={src} alt={alt} loading="lazy" />;
}
