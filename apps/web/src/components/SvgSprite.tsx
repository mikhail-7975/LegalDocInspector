import type { CSSProperties } from "react";

/** SVG-спрайт значков из макета `technical_specification/interface/index.html` */
export function SvgSprite() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" style={{ display: "none" }} aria-hidden="true">
      <defs>
        <symbol id="i-pdf" viewBox="0 0 24 24">
          <path
            fill="currentColor"
            d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm-1 2 5 5h-5V4zM8 12h8v2H8v-2zm0 4h8v2H8v-2z"
          />
        </symbol>
        <symbol id="i-xls" viewBox="0 0 24 24">
          <path
            fill="currentColor"
            d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm-1 2 5 5h-5V4zM9 13l1.5 2L9 17h2l.75-1.25L12.5 17h2l-1.5-2 1.5-2h-2l-.75 1.25L11 13H9z"
          />
        </symbol>
        <symbol id="i-upload" viewBox="0 0 24 24">
          <path fill="currentColor" d="M9 16h6v-6h4l-7-7-7 7h4v6zm-4 2h14v2H5v-2z" />
        </symbol>
        <symbol id="i-check" viewBox="0 0 24 24">
          <path fill="currentColor" d="M9 16.17 4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z" />
        </symbol>
        <symbol id="i-alert" viewBox="0 0 24 24">
          <path fill="currentColor" d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z" />
        </symbol>
        <symbol id="i-info" viewBox="0 0 24 24">
          <path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z" />
        </symbol>
        <symbol id="i-error" viewBox="0 0 24 24">
          <path
            fill="currentColor"
            d="M12 2C6.47 2 2 6.47 2 12s4.47 10 10 10 10-4.47 10-10S17.53 2 12 2zm5 13.59L15.59 17 12 13.41 8.41 17 7 15.59 10.59 12 7 8.41 8.41 7 12 10.59 15.59 7 17 8.41 13.41 12 17 15.59z"
          />
        </symbol>
        <symbol id="i-lock" viewBox="0 0 24 24">
          <path
            fill="currentColor"
            d="M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm-6 9c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm3.1-9H8.9V6c0-1.71 1.39-3.1 3.1-3.1 1.71 0 3.1 1.39 3.1 3.1v2z"
          />
        </symbol>
        <symbol id="i-text" viewBox="0 0 24 24">
          <path
            fill="currentColor"
            d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm-1 2 5 5h-5V4zM8 12h8v2H8v-2zm0 4h5v2H8v-2z"
          />
        </symbol>
        <symbol id="i-scan" viewBox="0 0 24 24">
          <path
            fill="currentColor"
            d="M3 5v4h2V5h4V3H5a2 2 0 0 0-2 2zm2 10H3v4a2 2 0 0 0 2 2h4v-2H5v-4zm14 4h-4v2h4a2 2 0 0 0 2-2v-4h-2v4zm0-10h2V5a2 2 0 0 0-2-2h-4v2h4v4zM12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z"
          />
        </symbol>
        <symbol id="i-clock" viewBox="0 0 24 24">
          <path
            fill="currentColor"
            d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67V7z"
          />
        </symbol>
        <symbol id="i-queue" viewBox="0 0 24 24">
          <path fill="currentColor" d="M4 14h4v-4H4v4zm0 5h4v-4H4v4zM4 9h4V5H4v4zm5 15h12v-4H9v4zm0-5h12v-4H9v4zm0-14v4h12V5H9z" />
        </symbol>
        <symbol id="i-download" viewBox="0 0 24 24">
          <path fill="currentColor" d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z" />
        </symbol>
        <symbol id="i-user" viewBox="0 0 24 24">
          <path
            fill="currentColor"
            d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"
          />
        </symbol>
        <symbol id="i-bell" viewBox="0 0 24 24">
          <path
            fill="currentColor"
            d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.89 2 2 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z"
          />
        </symbol>
        <symbol id="i-spinner" viewBox="0 0 24 24">
          <path
            fill="currentColor"
            d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46A7.93 7.93 0 0 0 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74A7.93 7.93 0 0 0 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"
          />
        </symbol>
        <symbol id="i-trash" viewBox="0 0 24 24">
          <path fill="currentColor" d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z" />
        </symbol>
        <symbol id="i-refresh" viewBox="0 0 24 24">
          <path
            fill="currentColor"
            d="M17.65 6.35A7.958 7.958 0 0 0 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08A5.99 5.99 0 0 1 12 18c-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"
          />
        </symbol>
        <symbol id="i-chevron-left" viewBox="0 0 24 24">
          <path fill="currentColor" d="M15.41 16.59 10.83 12l4.58-4.59L14 6l-6 6 6 6 1.41-1.41z" />
        </symbol>
        <symbol id="i-chevron-right" viewBox="0 0 24 24">
          <path fill="currentColor" d="M8.59 16.59 13.17 12 8.59 7.41 10 6l6 6-6 6-1.41-1.41z" />
        </symbol>
        <symbol id="i-close" viewBox="0 0 24 24">
          <path fill="currentColor" d="M19 6.41 17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" />
        </symbol>
      </defs>
    </svg>
  );
}

export function Icon({
  id,
  className,
  style,
}: {
  id: string;
  className?: string;
  style?: CSSProperties;
}) {
  return (
    <svg className={className ?? "icon"} style={style} aria-hidden="true">
      <use href={`#${id}`} />
    </svg>
  );
}
