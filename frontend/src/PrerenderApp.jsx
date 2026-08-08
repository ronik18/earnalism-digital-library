import { StaticRouter } from "react-router-dom";
import { AppProviders, AppRouterContent } from "./App";

export default function PrerenderApp({ location = "/" }) {
  return (
    <AppProviders>
      <StaticRouter location={location}>
        <AppRouterContent />
      </StaticRouter>
    </AppProviders>
  );
}
