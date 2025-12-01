import { Link } from 'react-router-dom';

const NotFound = () => (
  <div className="flex flex-col items-center justify-center gap-4 py-24">
    <h1 className="text-4xl font-bold">404</h1>
    <p className="text-slate-600 dark:text-slate-300">The page you are looking for could not be found.</p>
    <Link
      to="/"
      className="rounded-lg bg-primary px-6 py-3 font-semibold text-white shadow-card transition hover:bg-primary/90"
    >
      Return home
    </Link>
  </div>
);

export default NotFound;
