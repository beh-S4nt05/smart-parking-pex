declare module '*.css' {
  const content: { [className: string]: string };
  export default content;
}

declare module '*.css' {
  const styles: { [key: string]: string };
  export default styles;
}