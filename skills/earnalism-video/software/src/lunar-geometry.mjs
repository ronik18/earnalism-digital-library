// Idealized phase cycle: fixed sunlight from the left; diagram is not to scale.
export const litFraction = phase => (1 - Math.cos(2 * Math.PI * phase)) / 2;
export const orbitalPosition = (phase, cx=350, cy=320, radius=210) => ({x:cx-radius*Math.cos(2*Math.PI*phase),y:cy-radius*Math.sin(2*Math.PI*phase)});
