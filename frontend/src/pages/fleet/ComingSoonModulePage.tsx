import { Link } from "react-router-dom";

/** Placeholder for fleet modules not yet implemented. */
export function ComingSoonModulePage({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="page fleet-module-page">
      <header className="page-header">
        <p className="fleet-module-crumb">
          <Link to="/">Fleet</Link>
          <span aria-hidden="true"> / </span>
          {title}
        </p>
        <h1>{title}</h1>
        <p className="subtitle">{description}</p>
      </header>
      <section className="panel">
        <h2>Coming soon</h2>
        <p className="muted">
          This module is planned for the Fleet system. Fuel Requests and Admin (vehicles) are
          available now from the portal.
        </p>
        <Link to="/" className="button-link">
          Back to Fleet portal
        </Link>
      </section>
    </div>
  );
}
