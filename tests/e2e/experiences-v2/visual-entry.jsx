import { createRoot } from "react-dom/client";
import "../../../frontend/src/design-system/tokens.css";
import ReaderExperienceV2 from "../../../frontend/src/experiences-v2/reader/ReaderExperienceV2";
import ListenerExperienceV2 from "../../../frontend/src/experiences-v2/listener/ListenerExperienceV2";
import AboutExperienceV2 from "../../../frontend/src/experiences-v2/about/AboutExperienceV2";

const panel = new URLSearchParams(window.location.search).get("panel");
const component = panel === "listener"
  ? <ListenerExperienceV2 fixture />
  : panel === "about"
    ? <AboutExperienceV2 buildLabel="Earnalism v1.0" />
    : <ReaderExperienceV2 />;

createRoot(document.getElementById("root")).render(component);
