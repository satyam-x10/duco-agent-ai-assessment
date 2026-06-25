import React from 'react';
import { Link, NavLink } from 'react-router-dom';

export const Header: React.FC = () => {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-slate-200 bg-white/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Branding Logo */}
        <div className="flex items-center gap-3">
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600 text-white shadow-sm transition-all group-hover:bg-blue-700">
              {/* Medical/Insurance Shield SVG Icon */}
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={2}
                stroke="currentColor"
                className="h-5 w-5"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M9 12.75 11.25 15 15 9.75M21 12c0 1.268-.63 2.39-1.593 3.068a3.745 3.745 0 0 1-1.043 3.296 3.745 3.745 0 0 1-3.296 1.043A3.745 3.745 0 0 1 12 21c-1.268 0-2.39-.63-3.068-1.593a3.746 3.746 0 0 1-3.296-1.043 3.745 3.745 0 0 1-1.043-3.296A3.745 3.745 0 0 1 3 12c0-1.268.63-2.39 1.593-3.068a3.745 3.745 0 0 1 1.043-3.296 3.746 3.746 0 0 1 3.296-1.043A3.746 3.746 0 0 1 12 3c1.268 0 2.39.63 3.068 1.593a3.746 3.746 0 0 1 3.296 1.043 3.746 3.746 0 0 1 1.043 3.296A3.745 3.745 0 0 1 21 12Z"
                />
              </svg>
            </div>
            <div className="flex flex-col">
              <span className="text-lg font-bold tracking-tight text-slate-900 leading-none">
                DuCO-Agent
              </span>
              <span className="text-[10px] font-medium text-slate-500 tracking-wider uppercase mt-0.5">
                Enterprise COB Platform
              </span>
            </div>
          </Link>
        </div>

        {/* Global Navigation Links */}
        <nav className="hidden md:flex items-center gap-6">
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              `text-sm font-semibold transition-colors ${
                isActive ? 'text-blue-600' : 'text-slate-600 hover:text-blue-600'
              }`
            }
          >
            Dashboard
          </NavLink>
          <NavLink
            to="/intake"
            className={({ isActive }) =>
              `text-sm font-semibold transition-colors ${
                isActive ? 'text-blue-600' : 'text-slate-600 hover:text-blue-600'
              }`
            }
          >
            Intake
          </NavLink>
          <NavLink
            to="/results"
            className={({ isActive }) =>
              `text-sm font-semibold transition-colors ${
                isActive ? 'text-blue-600' : 'text-slate-600 hover:text-blue-600'
              }`
            }
          >
            COB Results
          </NavLink>
        </nav>

        {/* System Status Indicators */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700 ring-1 ring-inset ring-emerald-600/10">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
            Vite Server Active
          </div>
        </div>
      </div>
    </header>
  );
};
