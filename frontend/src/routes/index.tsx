import { createBrowserRouter } from 'react-router-dom';
import { AppLayout } from '../layouts/AppLayout';
import { HomePage } from '../pages/Home/HomePage';
import { IntakePage } from '../pages/Intake/IntakePage';
import { ResultsPage } from '../pages/Results/ResultsPage';
import { HistoryPage } from '../pages/History/HistoryPage';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      {
        path: '',
        element: <HomePage />,
      },
      {
        path: 'intake',
        element: <IntakePage />,
      },
      {
        path: 'results',
        element: <ResultsPage />,
      },
      {
        path: 'history',
        element: <HistoryPage />,
      },
    ],
  },
]);


