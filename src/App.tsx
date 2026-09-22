import {
  createRouter,
  createRootRoute,
  createRoute,
  RouterProvider,
  Outlet,
} from '@tanstack/react-router';

import HomePage from './pages/HomePage';
import AboutPage from './pages/AboutPage';
import SolarPage from './pages/SolarPage';
import HowItWorksPage from './pages/HowItWorksPage';
import ServicesPage from './pages/ServicesPage';
import ProjectsPage from './pages/ProjectsPage';
import FaqPage from './pages/FaqPage';
import ContactPage from './pages/ContactPage';
import LoginPage from './pages/LoginPage';
import StaffLoginPage from './pages/StaffLoginPage';
import ClientDashboardPage from './pages/ClientDashboardPage';
import AdminConsolePage from './pages/AdminConsolePage';

// Root route — renders children via <Outlet />
const rootRoute = createRootRoute({
  component: () => <Outlet />,
});

const indexRoute = createRoute({ getParentRoute: () => rootRoute, path: '/', component: HomePage });
const aboutRoute = createRoute({ getParentRoute: () => rootRoute, path: '/about', component: AboutPage });
const solarRoute = createRoute({ getParentRoute: () => rootRoute, path: '/solar', component: SolarPage });
const howItWorksRoute = createRoute({ getParentRoute: () => rootRoute, path: '/how-it-works', component: HowItWorksPage });
const servicesRoute = createRoute({ getParentRoute: () => rootRoute, path: '/services', component: ServicesPage });
const projectsRoute = createRoute({ getParentRoute: () => rootRoute, path: '/projects', component: ProjectsPage });
const faqRoute = createRoute({ getParentRoute: () => rootRoute, path: '/faq', component: FaqPage });
const contactRoute = createRoute({ getParentRoute: () => rootRoute, path: '/contact', component: ContactPage });
const loginRoute = createRoute({ getParentRoute: () => rootRoute, path: '/login', component: LoginPage });
const staffLoginRoute = createRoute({ getParentRoute: () => rootRoute, path: '/staff-login', component: StaffLoginPage });
const clientDashboardRoute = createRoute({ getParentRoute: () => rootRoute, path: '/client/dashboard', component: ClientDashboardPage });
const adminDashboardRoute = createRoute({ getParentRoute: () => rootRoute, path: '/admin/dashboard', component: AdminConsolePage });
const superAdminDashboardRoute = createRoute({ getParentRoute: () => rootRoute, path: '/super-admin/dashboard', component: AdminConsolePage });
const primaryAdminDashboardRoute = createRoute({ getParentRoute: () => rootRoute, path: '/primary-admin/dashboard', component: AdminConsolePage });

const routeTree = rootRoute.addChildren([
  indexRoute,
  aboutRoute,
  solarRoute,
  howItWorksRoute,
  servicesRoute,
  projectsRoute,
  faqRoute,
  contactRoute,
  loginRoute,
  staffLoginRoute,
  clientDashboardRoute,
  adminDashboardRoute,
  superAdminDashboardRoute,
  primaryAdminDashboardRoute,
]);

export const router = createRouter({ routeTree });

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router;
  }
}

export default function App() {
  return <RouterProvider router={router} />;
}
