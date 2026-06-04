import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { UserCircle, LogOut, Plus, Check } from 'lucide-react';
import { getAllAccounts, getActiveAccountIndex, switchAccount, removeAccount, getDefaultRoute } from '../../context/session';
import { logoutRequest } from '../../services/client';

export default function AccountSwitcher({ onAddAccount }) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);
  const navigate = useNavigate();

  const accounts = getAllAccounts();
  const activeIndex = getActiveAccountIndex();
  const activeAccount = accounts[activeIndex];

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  if (!accounts || accounts.length === 0) return null;

  const handleSwitch = (index) => {
    switchAccount(index);
    setIsOpen(false);
    // Reload to ensure context and routers mount with correct user
    window.location.href = getDefaultRoute(accounts[index].user);
  };

  const handleSignOut = async (index, e) => {
    e.stopPropagation();
    try {
      await logoutRequest();
    } catch (err) {
      console.error(err);
    }
    removeAccount(index);
    setIsOpen(false);

    const remaining = getAllAccounts();
    if (remaining.length === 0) {
      window.location.href = '/login';
    } else {
      window.location.href = getDefaultRoute(remaining[getActiveAccountIndex()].user);
    }
  };

  const getRoleLabel = (role) => {
    if (role === 'platform_admin') return 'Platform Admin';
    if (role === 'super_admin') return 'Super Admin';
    if (role === 'category_admin') return 'Category Admin';
    return 'Learner';
  };

  return (
    <div className="relative z-50" ref={dropdownRef}>
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 p-2 hover:bg-gray-100 rounded-lg transition-colors"
      >
        <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-bold">
          {activeAccount?.user?.name ? activeAccount.user.name[0].toUpperCase() : 'U'}
        </div>
        <div className="text-left hidden sm:block">
          <p className="text-sm font-semibold text-gray-800 leading-none">
            {activeAccount?.user?.name || 'User'}
          </p>
          <p className="text-xs text-gray-500 mt-1">
            {getRoleLabel(activeAccount?.user?.role)}
          </p>
        </div>
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-72 bg-white rounded-xl shadow-xl border border-gray-100 overflow-hidden transform transition-all duration-200">
          <div className="bg-gray-50 p-4 border-b border-gray-100">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
              {accounts.length > 1 ? "Your Accounts" : "Your Account"}
            </p>
          </div>
          
          <div className="max-h-64 overflow-y-auto">
            {accounts.map((acc, index) => {
              const isActive = index === activeIndex;
              return (
                <div 
                  key={index} 
                  className={`p-3 border-b border-gray-50 transition-colors flex items-center justify-between cursor-pointer ${isActive ? 'bg-blue-50' : 'hover:bg-gray-50'}`}
                  onClick={() => !isActive && handleSwitch(index)}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center shrink-0">
                      <UserCircle className="w-6 h-6 text-gray-500" />
                    </div>
                    <div className="flex flex-col">
                      <span className="text-sm font-semibold text-gray-800">
                        {acc.user?.name}
                      </span>
                      <span className="text-xs text-gray-500 truncate w-32">
                        {acc.user?.email}
                      </span>
                      <span className="text-xs font-medium text-blue-600 mt-0.5">
                        {getRoleLabel(acc.user?.role)}
                      </span>
                    </div>
                  </div>
                  
                  <div className="flex flex-col items-end gap-2">
                    {isActive && <Check className="w-5 h-5 text-blue-600" />}
                    <button 
                      onClick={(e) => handleSignOut(index, e)}
                      className="p-1 hover:bg-red-50 rounded text-red-500 transition-colors"
                      title="Sign out of this account"
                    >
                      <LogOut className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="p-2 border-t border-gray-100 bg-white">
            <button
              onClick={() => {
                setIsOpen(false);
                if (onAddAccount) {
                  onAddAccount();
                } else {
                  navigate('/login', { state: { addAccount: true } });
                }
              }}
              className="w-full flex items-center gap-2 p-2 text-sm font-semibold text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <div className="w-8 h-8 rounded-full border-2 border-dashed border-gray-300 flex items-center justify-center">
                <Plus className="w-4 h-4 text-gray-500" />
              </div>
              Add another account
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
