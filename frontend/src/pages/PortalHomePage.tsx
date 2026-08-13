import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import {
  canAccessEncode,
  canAccessFleetVehicles,
  canAccessMasterData,
  canManageUsers,
  canSeeComingSoonFleetModules,
} from "../utils/roles";

type PortalCard = {
  key: string;
  to: string;
  title: string;
  description: string;
  icon: "vehicle" | "renewal" | "fuel" | "pms" | "repair" | "insurance" | "admin";
  tone: "blue" | "teal" | "amber" | "green" | "slate" | "rose" | "navy";
  visible: boolean;
  comingSoon?: boolean;
};

function PortalIcon({ name }: { name: PortalCard["icon"] }) {
  switch (name) {
    case "vehicle":
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path
            fill="currentColor"
            d="M5 11 6.5 6.5h11L19 11h1a1 1 0 0 1 1 1v6h-2v-1H5v1H3v-6a1 1 0 0 1 1-1zm2.2-3 -.8 2.5h11.2L16.8 8zM6.5 14.5a1.25 1.25 0 1 0 0-2.5 1.25 1.25 0 0 0 0 2.5m11 0a1.25 1.25 0 1 0 0-2.5 1.25 1.25 0 0 0 0 2.5"
          />
        </svg>
      );
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
          <path
            fill="currentColor"
            d="m21.7 13.35-1 1-2.05-2.05 1-1a.5.5 0 0 1 .7 0l1.35 1.35c.2.2.2.5 0 .7M5 18.5 14.9 8.6l2.05 2.05L7.05 20.55H5z"
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
  const role = user?.role;
  const fuelTo = canAccessEncode(role) ? "/encode" : "/fuel";

  const cards: PortalCard[] = [
    {
      key: "vehicles",
      to: "/fleet/vehicles",
      title: "Vehicles",
      description: "Fleet master file, plates, company assignment",
      icon: "vehicle",
      tone: "blue",
      visible: canAccessFleetVehicles(role),
    },
    {
      key: "renewals",
      to: "/fleet/registrations",
      title: "Registrations",
      description: "OR/CR renewals, LTO dates, and alerts",
      icon: "renewal",
      tone: "teal",
      visible: canSeeComingSoonFleetModules(role),
      comingSoon: true,
    },
    {
      key: "fuel",
      to: fuelTo,
      title: "Fuel",
      description: "Requests, approvals, PO, billing, and reports",
      icon: "fuel",
      tone: "amber",
      visible: true,
    },
    {
      key: "pms",
      to: "/fleet/pms",
      title: "PMS",
      description: "Preventive maintenance schedules and due work",
      icon: "pms",
      tone: "green",
      visible: canSeeComingSoonFleetModules(role),
      comingSoon: true,
    },
    {
      key: "repairs",
      to: "/fleet/repairs",
      title: "Repairs",
      description: "Work orders, shops, and repair costs",
      icon: "repair",
      tone: "rose",
      visible: canSeeComingSoonFleetModules(role),
      comingSoon: true,
    },
    {
      key: "insurance",
      to: "/fleet/insurance",
      title: "Insurance",
      description: "Policies, expiry tracking, and claims",
      icon: "insurance",
      tone: "slate",
      visible: canSeeComingSoonFleetModules(role),
      comingSoon: true,
    },
    {
      key: "admin",
      to: "/master-data",
      title: "Admin",
      description: "Vendors, companies, users, and system setup",
      icon: "admin",
      tone: "navy",
      visible: canAccessMasterData(role) || canManageUsers(role),
    },
  ];

  const visibleCards = cards.filter((card) => card.visible);

  return (
    <div className="portal-home">
      <p className="portal-eyebrow">
        <span className="portal-eyebrow-mark" aria-hidden="true" />
        Fleet Management System
      </p>
      <h1 className="portal-welcome">Welcome</h1>
      <p className="portal-lead">Select a module to get started.</p>

      <div className="portal-card-grid">
        {visibleCards.map((card) => (
          <Link
            key={card.key}
            to={card.to}
            className={`portal-card tone-${card.tone}${card.comingSoon ? " coming-soon" : ""}`}
          >
            <span className="portal-card-icon">
              <PortalIcon name={card.icon} />
            </span>
            <h2>{card.title}</h2>
            <p>{card.description}</p>
            {card.comingSoon && <span className="portal-soon-badge">Coming soon</span>}
          </Link>
        ))}
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
