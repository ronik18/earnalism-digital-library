import { useNavigate } from "react-router-dom";
import useSEO from "../../hooks/useSEO";
import AboutExperienceV2 from "./AboutExperienceV2";

export default function AboutExperienceV2Route() {
  const navigate = useNavigate();
  useSEO({
    title: "About Earnalism — Bengali and English Digital Library",
    description: "Earnalism is a calm Bengali and English digital library where reader-ready classics are published with release truth before every public claim.",
  });
  return <AboutExperienceV2 onNavigate={(target) => {
    if (target === "home") navigate("/");
    if (target === "library" || target === "search") navigate("/library");
    if (target === "passes") navigate("/pricing");
    if (target === "profile") navigate("/account");
  }} />;
}
