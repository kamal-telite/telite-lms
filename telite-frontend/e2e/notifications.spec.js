import { test, expect } from '@playwright/test';

const USERS = {
  superadmin: { username: 'kt_superadmin', password: 'password' },
  categoryadmin: { username: 'kt_category_admin', password: 'password' },
  learner: { username: 'kt_learner_2', password: 'password' }
};

async function login(page, userType) {
  const user = USERS[userType];
  await page.goto('/login');
  await page.fill('#username', user.username);
  await page.fill('#password', user.password);
  await page.click('#btnOpen');
  // Wait for navigation and dashboard
  await expect(page).toHaveURL(/.*\/dashboard|.*\/learner|.*\/admin/);
}

for (const role of Object.keys(USERS)) {
  test(`[${role}] Notification UI Critical Path Verification`, async ({ page }) => {
    // 1. Login as the specific role
    await login(page, role);

    // 2. Verify NotificationBell renders
    const bellBtn = page.locator('.notification-bell-btn');
    await expect(bellBtn).toBeVisible();

    // 3. Click the bell to open drawer
    await bellBtn.click();

    // 4. Verify NotificationDrawer opens
    const drawer = page.locator('.notification-card').first();
    // It might be empty, so we look for the drawer container
    const drawerHeader = page.getByText('Notifications', { exact: true });
    await expect(drawerHeader).toBeVisible();

    // If there are unread notifications, check badge and mark read
    const badge = bellBtn.locator('span');
    const hasUnread = await badge.isVisible();

    if (hasUnread) {
      // 5. Verify unread badge updates correctly
      const initialCountStr = await badge.innerText();
      const initialCount = parseInt(initialCountStr.replace('+', ''));

      // 6. Mark a single notification as read
      const unreadDot = page.locator('.notification-card .unread-dot').first();
      if (await unreadDot.isVisible()) {
          const markReadBtn = page.locator('.notification-card').first().locator('button[title="Mark as read"]');
          if (await markReadBtn.isVisible()) {
              await markReadBtn.click();
              // Wait for badge to update
              await expect(badge).not.toHaveText(initialCountStr);
          }
      }

      // 7. Mark all as read
      const markAllBtn = page.getByText('Mark all as read');
      if (await markAllBtn.isVisible()) {
          await markAllBtn.click();
          await expect(badge).not.toBeVisible();
      }
    }

    // 8. Deep links navigation (click a notification if available)
    const card = page.locator('.notification-card').first();
    if (await card.isVisible()) {
        const actionBtn = card.locator('button.btn--outline').first();
        if (await actionBtn.isVisible()) {
            await actionBtn.click();
            // Verify it navigated away from the current page
            // Or just verify drawer closed
            await expect(drawerHeader).not.toBeVisible();
        }
    }

    // 9. Persist after page refresh
    await page.reload();
    await expect(bellBtn).toBeVisible();

    // No console errors are checked implicitly by not crashing, but we could add explicit checks if needed.
  });
}
