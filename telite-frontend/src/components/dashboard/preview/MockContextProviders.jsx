import React, { createContext, useContext, useMemo } from 'react';
import { BrowserRouter } from 'react-router-dom';

// We override the Auth and App contexts to provide mock data for the preview shell.
export const MockAuthContext = createContext(null);
export const MockAppContext = createContext(null);

export function MockContextProviders({ children, role }) {
  // Mock Session Data based on selected role
  const session = useMemo(() => {
    if (role === 'learner') {
      return {
        user: { id: "mock-1", full_name: "Jane Learner", email: "jane@example.com", role: "learner", org_id: 1, avatar_initials: "JL", is_active: true },
        token: "mock-token",
        tenant: { slug: "preview", name: "Preview Tenant", domain: "preview.telitelms.com" }
      };
    } else if (role === 'category_admin') {
      return {
        user: { id: "mock-2", full_name: "John Admin", email: "admin@example.com", role: "category_admin", org_id: 1, avatar_initials: "JA", is_active: true },
        token: "mock-token",
        tenant: { slug: "preview", name: "Preview Tenant", domain: "preview.telitelms.com" }
      };
    } else if (role === 'super_admin') {
      return {
        user: { id: "mock-3", full_name: "Sarah Super", email: "super@example.com", role: "super_admin", org_id: 1, avatar_initials: "SS", is_active: true },
        token: "mock-token",
        tenant: { slug: "preview", name: "Preview Tenant", domain: "preview.telitelms.com" }
      };
    }
    return null; // For public/login views
  }, [role]);

  // Mock App Data
  const appData = useMemo(() => {
    return {
      session,
      isAuthenticated: !!session,
      logout: () => console.log("Mock logout clicked"),
      // Add other mock functions/data required by LearnerLayout, CategoryAdminPage, etc.
      stats: {
        enrolled: 12,
        completed: 5,
        inProgress: 7,
      },
      recentCourses: [
        { id: "c1", title: "Introduction to Data Science", progress: 75, category: "Data" },
        { id: "c2", title: "Advanced React Patterns", progress: 30, category: "Engineering" },
      ]
    };
  }, [session]);

  return (
    <MockAuthContext.Provider value={session}>
      <MockAppContext.Provider value={appData}>
        {/* We use a scoped router specifically for the preview iframe equivalent */}
        {children}
      </MockAppContext.Provider>
    </MockAuthContext.Provider>
  );
}
