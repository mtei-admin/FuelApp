import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import {
  canAccessInsurancePortal,
  canAccessMasterData,
  canAccessPms,
  canManageUsers,
  prefersEncoderFuelPortal,
} from "../utils/roles";

type PortalCard = {
  key: string;
  to?: string;
  title: string;
  description: string;
  icon: "renewal" | "fuel" | "pms" | "repair" | "insurance" | "admin";
  tone: "teal" | "amber" | "green" | "slate" | "rose" | "navy";
  accessible: boolean;
  comingSoon?: boolean;
};

function PortalIcon({ name }: { name: PortalCard["icon"] }) {
  switch (name) {
    case "renewal":
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path
            fill="currentColor"
            d="M7 3h10a2 2 0 0 1 2 2v14l-7-3-7 3V5a2 2 0 0 1 2-2m0 2v11.1l5-2.1 5 2.1V5z"
          />
        </svg>
      );
    case "fuel":
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path
            fill="currentColor"
            d="M8 2h6a2 2 0 0 1 2 2v2h1a3 3 0 0 1 3 3v8a2 2 0 0 1-2 2h-1v1a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2m8 6v8h1V9a1 1 0 0 0-1-1m-8-4v16h6V4z"
          />
        </svg>
      );
    case "pms":
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path
            fill="currentColor"
            d="M12 2a10 10 0 1 1 0 20 10 10 0 0 1 0-20m0 2a8 8 0 1 0 .01 16.01A8 8 0 0 0 12 4m-.75 3h1.5v5.25l3.5 2.1-.75 1.25L11.25 13z"
          />
        </svg>
      );
    case "repair":
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          {/* Screwdriver diagonal ↘ */}
          <path
            fill="currentColor"
            d="M8.1 2.9c.4-.4 1-.4 1.4 0l2.1 2.1c.2.2.3.5.2.8l-.3.8 1.5 1.5-1.4 1.4-1.5-1.5-.8.3c-.3.1-.6 0-.8-.2L6.4 5.9c-.4-.4-.4-1 0-1.4zM12.4 9.7l1.4-1.4 7.5 7.5c.5.5.5 1.3 0 1.8l-.4.4c-.5.5-1.3.5-1.8 0z"
          />
          {/* Wrench diagonal ↗ */}
          <path
            fill="currentColor"
            d="M14.2 3.2c1.8-.5 3.7.2 4.8 1.8.3.5.5 1 .6 1.6l-2.3-.2c-.1-.3-.3-.5-.5-.7-.6-.7-1.6-.9-2.4-.5l-1.1.6 3.4 3.4.6-1.1c.4-.8.2-1.8-.5-2.4-.2-.2-.4-.4-.7-.5l-.2-2.3c.1 0 .2 0 .3 0zM9.9 9.9 3.3 16.5c-.5.5-.5 1.3 0 1.8l.4.4c.5.5 1.3.5 1.8 0L12.1 12z"
          />
        </svg>
      );
    case "insurance":
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path
            fill="currentColor"
            d="M12 2 4 5v6c0 5 3.4 9.4 8 11 4.6-1.6 8-6 8-11V5zm0 2.2 6 2.25V11c0 3.9-2.5 7.4-6 8.85C8.5 18.4 6 14.9 6 11V6.45z"
          />
        </svg>
      );
    case "admin":
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path
            fill="currentColor"
            d="M12 8a4 4 0 1 1 0 8 4 4 0 0 1 0-8m0-6 1.5 2.6 3-.5 1.5 2.6-2.4 1.9.9 2.9L12 13.5l-4.5 1.5.9-2.9-2.4-1.9L7.5 7.1l3 .5z"
          />
        </svg>
      );
    default:
      return null;
  }
}

export function PortalHomePage() {
  const { user } = useAuth();
  const fuelTo = prefersEncoderFuelPortal(user) ? "/encode" : "/fuel";
  const canAccessAdmin = canAccessMasterData(user) || canManageUsers(user);
  const canInsurance = canAccessInsurancePortal(user);
  const canPms = canAccessPms(user);

  const cards: PortalCard[] = [
    {
      key: "renewals",
      to: "/fleet/registrations",
      title: "Registrations",
      description: "OR/CR renewals, LTO dates, and alerts",
      icon: "renewal",
      tone: "teal",
      accessible: true,
    },
    {
      key: "fuel",
      to: fuelTo,
      title: "Fuel Requests",
      description: "Requests, approvals, PO, billing, and reports",
      icon: "fuel",
      tone: "amber",
      accessible: true,
    },
    {
      key: "pms",
      to: "/fleet/pms",
      title: "PMS",
      description: "Preventive maintenance schedules and due work",
      icon: "pms",
      tone: "green",
      accessible: canPms,
    },
    {
      key: "repairs",
      to: "/fleet/repairs",
      title: "Repairs",
      description: "Work orders, shops, and repair costs",
      icon: "repair",
      tone: "rose",
      accessible: true,
      comingSoon: true,
    },
    {
      key: "insurance",
      to: "/fleet/insurance",
      title: "Insurance",
      description: "Policies, expiry tracking, and claims",
      icon: "insurance",
      tone: "slate",
      accessible: canInsurance,
    },
    {
      key: "admin",
      to: "/master-data",
      title: "Admin",
      description: "Vehicles, vendors, companies, service centers, users, and system setup",
      icon: "admin",
      tone: "navy",
      accessible: canAccessAdmin,
    },
  ];

  return (
    <div className="portal-home">
      <p className="portal-eyebrow">
        <span className="portal-eyebrow-mark" aria-hidden="true" />
        Fleet Management System
      </p>
      <h1 className="portal-welcome">Welcome</h1>
      <p className="portal-lead">Select a module to get started.</p>

      <div className="portal-card-grid">
        {cards.map((card) => {
          const cardClass = `portal-card tone-${card.tone}${
            card.accessible ? "" : " portal-card-locked"
          }`;
          const cardBody = (
            <>
              <span className="portal-card-icon">
                <PortalIcon name={card.icon} />
              </span>
              <h2>{card.title}</h2>
              <p>{card.description}</p>
              {!card.accessible && <span className="portal-soon-badge">Coming soon</span>}
              {card.accessible && card.comingSoon && (
                <span className="portal-soon-badge">Coming soon</span>
              )}
            </>
          );

          if (card.accessible && card.to) {
            return (
              <Link key={card.key} to={card.to} className={cardClass}>
                {cardBody}
              </Link>
            );
          }

          return (
            <div key={card.key} className={cardClass} aria-disabled="true">
              {cardBody}
            </div>
          );
        })}
      </div>

      <section className="portal-install">
        <h3>Install Fleet on your phone</h3>
        <p>
          <strong>iPhone:</strong> Safari → Share → Add to Home Screen
          <br />
          <strong>Android:</strong> Chrome menu → Install app or Add to Home screen
        </p>
        <p className="portal-install-note">An internet connection is required to use Fleet.</p>
      </section>
    </div>
  );
}
