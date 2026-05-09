import React, { useState, useRef, useEffect } from 'react';
import { ZoomIn, ZoomOut, X } from 'lucide-react';

const SmartImage = ({ src, alt, srcset, dominantColor, type = 'inline', className = '' }) => {
  const [loaded, setLoaded] = useState(false);
  const [zoomed, setZoomed] = useState(false);
  const imgRef = useRef(null);

  useEffect(() => {
    const img = imgRef.current;
    if (!img) return;
    const handleLoad = () => setLoaded(true);
    const handleError = () => setLoaded(true);
    img.addEventListener('load', handleLoad);
    img.addEventListener('error', handleError);
    return () => {
      img.removeEventListener('load', handleLoad);
      img.removeEventListener('error', handleError);
    };
  }, [src]);

  const handleClick = () => {
    if (type === 'lightbox') setZoomed(true);
  };

  const closeZoom = () => setZoomed(false);

  return (
    <>
      <figure className={`reader-img ${type} ${className}`} style={{ backgroundColor: dominantColor || '#f5f0e8' }}>
        <img
          ref={imgRef}
          src={src}
          srcSet={srcset}
          alt={alt}
          onClick={handleClick}
          className={loaded ? 'loaded' : 'loading'}
          loading="lazy"
        />
        {alt && <figcaption>{alt}</figcaption>}
      </figure>
      {zoomed && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80" onClick={closeZoom}>
          <img src={src} srcSet={srcset} alt={alt} className="max-w-full max-h-full" />
          <button onClick={closeZoom} className="absolute top-4 right-4 text-white">
            <X size={24} />
          </button>
        </div>
      )}
    </>
  );
};

export default SmartImage;
