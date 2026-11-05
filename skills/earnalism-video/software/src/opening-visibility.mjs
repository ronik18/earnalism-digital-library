// Keep the explanatory subject visible on the first frame; later scenes may
// ease in. This controls visibility, not proof of an informative visual payoff.
export const subjectOpacity=(seconds,sceneStart,isOpening)=>isOpening?1:Math.max(0,Math.min(1,(seconds-sceneStart)*3));
