/**
 * Chrysalias.com Global Unified Engine
 * Full PostgreSQL Database Integration — No localStorage, no mock data.
 * Auth token stored in sessionStorage only (cleared on browser close).
 */

(function () {
  'use strict';

  const hostname = window.location.hostname;
  const isLocalhost = (hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '');
  const API_BASE = isLocalhost
    ? 'http://127.0.0.1:8000/api'
    : 'https://chrysalias.onrender.com/api';

  window.EscrowApp = {
    API_BASE: API_BASE,

    /* ── Auth Token & User ─────────────────────────────────── */
    getToken: function () {
      return sessionStorage.getItem('chrysalias_token') || null;
    },

    setToken: function (token) {
      if (token) sessionStorage.setItem('chrysalias_token', token);
      else sessionStorage.removeItem('chrysalias_token');
    },

    getUser: function () {
      try {
        const u = sessionStorage.getItem('chrysalias_active_user');
        return u ? JSON.parse(u) : null;
      } catch (e) { return null; }
    },

    setUser: function (userObj) {
      if (!userObj) sessionStorage.removeItem('chrysalias_active_user');
      else sessionStorage.setItem('chrysalias_active_user', JSON.stringify(userObj));
    },

    getAuthHeaders: function () {
      const token = this.getToken();
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = 'Token ' + token;
      return headers;
    },

    logout: function () {
      const token = this.getToken();
      try {
        fetch(API_BASE + '/auth/logout/', {
          method: 'POST',
          headers: this.getAuthHeaders()
        }).catch(function () {});
      } catch (e) {}
      sessionStorage.clear();
      window.location.href = 'login.html';
    },

    /* ── Fetch User from Backend ──────────────────────────── */
    fetchMe: async function () {
      try {
        const resp = await fetch(API_BASE + '/auth/me/', {
          headers: this.getAuthHeaders()
        });
        if (resp.ok) {
          const data = await resp.json();
          if (data.authenticated && data.user) {
            this.setUser(data.user);
            return data.user;
          }
        }
      } catch (e) {
        console.warn('Could not fetch user profile from backend.');
      }
      return this.getUser();
    },

    /* ── Transactions — Always from PostgreSQL ────────────── */
    fetchBackendTransactions: async function () {
      const token = this.getToken();
      if (!token) return [];
      try {
        const resp = await fetch(API_BASE + '/transactions/', {
          headers: this.getAuthHeaders()
        });
        if (resp.ok) {
          const data = await resp.json();
          if (Array.isArray(data)) {
            return data.map(function (tx) {
              const pp = tx.partnered_payment || {};
              const totalAmt = parseFloat(tx.amount) || 0;
              const partnerAmt = parseFloat(pp.partner_amount) || 0;
              const myContrib = partnerAmt > 0 ? Math.max(0, totalAmt - partnerAmt) : 0;

              return {
                id: tx.tx_id,
                tx_id: tx.tx_id,
                title: tx.title,
                description: tx.description || '',
                role: tx.initiator_role || 'Buyer',
                counterparty: tx.seller_email_display || tx.buyer_email_display || '',
                amount: totalAmt,
                buyerPrice: totalAmt,
                price: totalAmt,
                currency: tx.currency || 'USD',
                category: tx.category || '',
                status: tx.status,
                inspectionPeriod: tx.inspection_period,
                inspectionDays: tx.inspection_period,
                date: tx.created_at ? tx.created_at.split('T')[0] : '',
                isPartneredPayment: tx.is_partnered,
                is_partnered: tx.is_partnered,
                partnerEmail: pp.partner_email || '',
                myContribution: myContrib,
                partnerContribution: partnerAmt,
                // Amount tracking
                primary_amount_paid: parseFloat(tx.primary_amount_paid) || 0,
                partner_amount_paid: parseFloat(tx.partner_amount_paid) || 0,
              };
            });
          }
        }
      } catch (e) {
        console.warn('Chrysalias API unreachable:', e);
      }
      return [];
    },

    /* ── Create Transaction via API ───────────────────────── */
    addTransaction: async function (newTx) {
      const token = this.getToken();
      if (!token) {
        console.warn('Not authenticated — cannot create transaction.');
        return null;
      }
      try {
        const payload = {
          title:              newTx.title,
          description:        newTx.description || '',
          initiator_role:     newTx.role || 'Buyer',
          amount:             newTx.amount || newTx.price || newTx.buyerPrice || 0,
          currency:           newTx.currency || 'USD',
          category:           newTx.category || 'General Merchandise',
          inspection_period:  newTx.inspectionDays || newTx.inspectionPeriod || 2,
          seller_email:       newTx.sellerEmail || '',
          seller_phone:       newTx.sellerPhone || '',
          buyer_email:        newTx.buyerEmail || '',
          is_partnered:       !!newTx.isPartneredPayment,
          partner_email:      newTx.partnerEmail || '',
          my_contribution:    newTx.myContribution || 0,
          partner_contribution: newTx.partnerContribution || 0,
        };
        const resp = await fetch(API_BASE + '/transactions/', {
          method: 'POST',
          headers: this.getAuthHeaders(),
          body: JSON.stringify(payload)
        });
        if (resp.ok) {
          const created = await resp.json();
          return created;
        } else {
          const err = await resp.json().catch(function () { return {}; });
          console.error('Transaction creation failed:', err);
          return null;
        }
      } catch (e) {
        console.error('Network error creating transaction:', e);
        return null;
      }
    },

    /* ── Email Notifications ──────────────────────────────── */
    sendEmail: function (type, email, extraData) {
      if (!email) return;
      var user = this.getUser() || { name: 'Valued Customer', email: email };
      var payload = Object.assign({
        type: type,
        email: email,
        name: user.name || 'Valued Customer',
      }, extraData || {});
      try {
        fetch(API_BASE + '/auth/send-email/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        }).catch(function () {});
      } catch (e) {}
    },

    /* ── Fee Calculator ───────────────────────────────────── */
    calculateFees: function (amount) {
      amount = parseFloat(amount) || 0;
      var feeRate = 0.0325;
      if (amount > 25000) feeRate = 0.0125;
      else if (amount > 5000) feeRate = 0.022;
      var escrowFee = Math.max(25, amount * feeRate);
      var processingFee = amount * 0.015;
      return { escrowFee: escrowFee, processingFee: processingFee, totalFee: escrowFee + processingFee };
    },

        /* ── Toast Notification ───────────────────────────────── */
    showToast: function (msg, type) {
      type = type || 'success';
      let container = document.querySelector('.toast-container');
      if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        container.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:99999;display:flex;flex-direction:column;gap:10px;pointer-events:none;';
        document.body.appendChild(container);
      }
      const toast = document.createElement('div');
      const isError = type === 'error';
      const borderColor = isError ? '#ef4444' : '#3cb95d';
      const icon = isError 
        ? '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>'
        : '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#3cb95d" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>';

      toast.style.cssText = 'background:#002b49;color:#ffffff;padding:12px 20px;border-radius:8px;font-size:0.88rem;font-weight:600;box-shadow:0 10px 25px rgba(0,0,0,0.2);display:flex;align-items:center;gap:10px;pointer-events:auto;transition:all 0.3s ease;transform:translateY(20px);opacity:0;border-left:4px solid ' + borderColor + ';';
      toast.innerHTML = icon + '<span>' + msg + '</span>';
      container.appendChild(toast);
      requestAnimationFrame(function () {
        toast.style.transform = 'translateY(0)';
        toast.style.opacity = '1';
      });
      setTimeout(function () {
        toast.style.transform = 'translateY(20px)';
        toast.style.opacity = '0';
        setTimeout(function () { toast.remove(); }, 300);
      }, 3500);
    },

    /* ── Header & Navigation Generator ───────────────────── */
    renderHeader: function (activePage) {
      activePage = activePage || '';
      var headerContainer = document.getElementById('app-header');
      if (!headerContainer) return;

      var path = window.location.pathname.toLowerCase();
      if (
        path.includes('login.html') ||
        path.includes('signup.html') ||
        path.includes('start-transaction.html')
      ) {
        headerContainer.innerHTML = '';
        return;
      }

      var isDashboard = activePage === 'dashboard' || path.includes('dashboard.html');
      var realUser = this.getUser();

      if (isDashboard && !realUser) {
        window.location.href = 'login.html';
        return;
      }

      var user = realUser || { name: 'Guest User', email: '' };
      var nameParts = user.name ? user.name.trim().split(' ') : ['User'];
      var initials = nameParts.length > 1
        ? (nameParts[0].charAt(0) + nameParts[nameParts.length - 1].charAt(0)).toUpperCase()
        : nameParts[0].substring(0, 2).toUpperCase();

      var avatarPic = user.profile_picture || user.avatar || '';
      var avatarContent = avatarPic
        ? '<div class="user-avatar-circle" style="background-image:url(' + avatarPic + ');background-size:cover;background-position:center;color:transparent;"></div>'
        : '<div class="user-avatar-circle">' + initials + '</div>';

      if (isDashboard) {
        headerContainer.innerHTML =
          '<header class="dashboard-header-bar">' +
          '  <div class="dashboard-header-container">' +
          '    <a href="index.html" class="dashboard-logo" title="Go to home page" style="display:flex;align-items:center;gap:10px;text-decoration:none;">' +
          '      <img src="build/images/chrysalias-logo-icon.png" alt="Chrysalias" style="height:32px;width:32px;border-radius:6px;object-fit:cover;">' +
          '      <span style="font-family: Montserrat,sans-serif;font-weight:800;font-size:1.45rem;color:#002b49;letter-spacing:-0.5px;">CHRYSALIAS<span style="color:#3cb95d">.COM</span></span>' +
          '    </a>' +
          '    <div class="dashboard-header-right">' +
          '      <div class="dashboard-user-profile-wrapper" id="userProfileBtn" style="cursor:pointer;" title="View Profile">' +
          '        <a href="profile.html" style="text-decoration:none;">' + avatarContent + '</a>' +
          '        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" id="userDropdownArrow"><path d="M6 9l6 6 6-6"/></svg>' +
          '        <div class="user-profile-dropdown" id="userDropdown">' +
          '          <div class="dropdown-user-info"><strong>' + user.name + '</strong><small>' + user.email + '</small></div>' +
          '          <hr>' +
          '          <a href="profile.html" class="dropdown-item">' +
          '            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:8px"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>My Profile' +
          '          </a>' +
          '          <a href="dashboard.html" class="dropdown-item">' +
          '            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:8px"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path></svg>Dashboard' +
          '          </a>' +
          '          <a href="#" class="dropdown-item logout-item" id="logoutBtn">' +
          '            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:8px"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path><polyline points="16 17 21 12 16 7"></polyline><line x1="21" y1="12" x2="9" y2="12"></line></svg>Log Out' +
          '          </a>' +
          '        </div>' +
          '      </div>' +
          '    </div>' +
          '  </div>' +
          '</header>';

        setTimeout(function () {
          var arrowBtn = document.getElementById('userDropdownArrow');
          var userDd = document.getElementById('userDropdown');
          var logoutBtn = document.getElementById('logoutBtn');
          if (arrowBtn && userDd) {
            arrowBtn.addEventListener('click', function (e) {
              e.stopPropagation();
              e.preventDefault();
              userDd.classList.toggle('show');
            });
          }
          if (logoutBtn) {
            logoutBtn.addEventListener('click', function (e) {
              e.preventDefault();
              window.EscrowApp.logout();
            });
          }
          document.addEventListener('click', function () {
            if (userDd) userDd.classList.remove('show');
          });
        }, 50);
        return;
      }

      // ── Public Page Header ──
      var loginBtn  = '<a href="login.html"  id="chrys-login-btn"  style="display:inline-flex;align-items:center;justify-content:center;padding:9px 22px;border-radius:7px;background:transparent;border:1.5px solid #01426a;color:#01426a;font-weight:600;font-size:0.88rem;text-decoration:none;white-space:nowrap;letter-spacing:0.2px;transition:all 0.2s;">Log In</a>';
      var signupBtn = '<a href="signup.html" id="chrys-signup-btn" style="display:inline-flex;align-items:center;justify-content:center;padding:9px 22px;border-radius:7px;background:#01426a;border:1.5px solid #01426a;color:#ffffff;font-weight:700;font-size:0.88rem;text-decoration:none;white-space:nowrap;letter-spacing:0.2px;transition:all 0.2s;">Sign Up</a>';
      var dashBtn   = '<a href="dashboard.html" id="chrys-dash-btn" style="display:inline-flex;align-items:center;justify-content:center;padding:9px 22px;border-radius:7px;background:transparent;border:1.5px solid #01426a;color:#01426a;font-weight:600;font-size:0.88rem;text-decoration:none;white-space:nowrap;letter-spacing:0.2px;transition:all 0.2s;">Dashboard</a>';
      var logoutBtn = '<a href="#" id="chrys-logout-link" style="display:inline-flex;align-items:center;justify-content:center;padding:9px 22px;border-radius:7px;background:#3cb95d;border:1.5px solid #3cb95d;color:#ffffff;font-weight:700;font-size:0.88rem;text-decoration:none;white-space:nowrap;letter-spacing:0.2px;transition:all 0.2s;">Log Out</a>';

      var desktopAuth = realUser ? (dashBtn + logoutBtn) : (loginBtn + signupBtn);
      var mobileAuth  = realUser
        ? '<a href="dashboard.html" style="display:block;padding:12px 0;color:#01426a;font-weight:600;text-decoration:none;border-bottom:1px solid #e8eef2;font-size:0.95rem;">Dashboard</a>' +
          '<a href="#" id="chrys-mobile-logout" style="display:block;padding:12px 0;color:#ef4444;font-weight:600;text-decoration:none;font-size:0.95rem;">Log Out</a>'
        : '<a href="login.html"  style="display:block;text-align:center;margin:6px 0;padding:11px;border-radius:7px;background:transparent;border:1.5px solid #01426a;color:#01426a;font-weight:600;text-decoration:none;font-size:0.95rem;">Log In</a>' +
          '<a href="signup.html" style="display:block;text-align:center;margin:6px 0;padding:11px;border-radius:7px;background:#01426a;color:#ffffff;font-weight:700;text-decoration:none;font-size:0.95rem;">Sign Up</a>';

      headerContainer.innerHTML =
        '<style>' +
        '#chrys-header{position:fixed;top:0;left:0;right:0;z-index:99999;width:100%;box-sizing:border-box;}' +
        '#chrys-navbar{background:#ffffff;padding:0 24px;box-shadow:0 1px 16px rgba(0,0,0,0.09);border-bottom:1px solid #e8eef2;}' +
        '#chrys-navbar-inner{max-width:1180px;margin:0 auto;display:flex;align-items:center;justify-content:space-between;height:66px;}' +
        '#chrys-logo{display:flex;align-items:center;gap:10px;text-decoration:none;flex-shrink:0;}' +
        '#chrys-desktop-actions{display:flex;align-items:center;gap:12px;flex-shrink:0;}' +
        '#chrys-hamburger{display:none;background:none;border:none;cursor:pointer;padding:6px;color:#01426a;flex-shrink:0;}' +
        '#chrys-mobile-drawer{display:none;position:fixed;top:66px;left:0;right:0;background:#ffffff;border-bottom:2px solid #e8eef2;box-shadow:0 8px 24px rgba(0,0,0,0.12);padding:16px 24px 24px;z-index:99998;}' +
        '#chrys-mobile-drawer.open{display:block;}' +
        '@media(max-width:768px){#chrys-desktop-actions{display:none !important;}#chrys-hamburger{display:flex !important;}}' +
        '</style>' +
        '<div id="chrys-header">' +
        '  <nav id="chrys-navbar">' +
        '    <div id="chrys-navbar-inner">' +
        '      <a id="chrys-logo" href="index.html" title="Chrysalias Home">' +
        '        <img src="build/images/chrysalias-logo-icon.png" alt="Chrysalias" style="height:32px;width:32px;object-fit:contain;flex-shrink:0;">' +
        '        <span style="font-family:Montserrat,sans-serif;font-weight:800;font-size:1.45rem;color:#01426a;letter-spacing:-0.5px;white-space:nowrap;">CHRYSALIAS<span style="color:#3cb95d;">.COM</span></span>' +
        '      </a>' +
        '      <div id="chrys-desktop-actions">' + desktopAuth + '</div>' +
        '      <button id="chrys-hamburger" aria-label="Open menu" aria-expanded="false">' +
        '        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>' +
        '      </button>' +
        '    </div>' +
        '  </nav>' +
        '  <div id="chrys-mobile-drawer">' + mobileAuth + '</div>' +
        '</div>';

      setTimeout(function () {
        document.body.style.paddingTop = '66px';
        var hamburger = document.getElementById('chrys-hamburger');
        var drawer    = document.getElementById('chrys-mobile-drawer');
        if (hamburger && drawer) {
          hamburger.addEventListener('click', function (e) {
            e.stopPropagation();
            var isOpen = drawer.classList.contains('open');
            drawer.classList.toggle('open', !isOpen);
            hamburger.setAttribute('aria-expanded', String(!isOpen));
            hamburger.innerHTML = isOpen
              ? '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>'
              : '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
          });
          document.addEventListener('click', function (e) {
            if (!drawer.contains(e.target) && e.target !== hamburger && !hamburger.contains(e.target)) {
              drawer.classList.remove('open');
              hamburger.setAttribute('aria-expanded', 'false');
              hamburger.innerHTML = '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>';
            }
          });
        }
        ['chrys-logout-link', 'chrys-mobile-logout'].forEach(function (id) {
          var el = document.getElementById(id);
          if (el) {
            el.addEventListener('click', function (e) {
              e.preventDefault();
              window.EscrowApp.logout();
            });
          }
        });
      }, 50);
    },

    renderFooter: function () {
      var footerContainer = document.getElementById('app-footer');
      if (!footerContainer) return;
      var path = window.location.pathname.toLowerCase();
      if (path.includes('dashboard.html') || path.includes('login.html') || path.includes('signup.html')) {
        footerContainer.innerHTML = '';
        return;
      }
      footerContainer.innerHTML =
        '<footer style="background-color:#002b49;color:#cbd5e1;padding:50px 20px 30px 20px;font-size:0.88rem;">' +
        '  <div style="max-width:1120px;margin:0 auto;display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:32px;text-align:left;">' +
        '    <div><h4 style="color:#ffffff;margin-top:0;font-family:Montserrat,sans-serif;">Consumer</h4>' +
        '      <ul style="list-style:none;padding:0;margin:0;line-height:2;">' +
        '        <li><a href="index.html" style="color:#94a3b8;">What is Chrysalias?</a></li>' +
        '        <li><a href="index.html" style="color:#94a3b8;">Domain Name Protection</a></li>' +
        '        <li><a href="index.html" style="color:#94a3b8;">Vehicle Protection</a></li>' +
        '      </ul></div>' +
        '    <div><h4 style="color:#ffffff;margin-top:0;font-family:Montserrat,sans-serif;">Account &amp; Support</h4>' +
        '      <ul style="list-style:none;padding:0;margin:0;line-height:2;">' +
        '        <li><a href="login.html" style="color:#94a3b8;">Sign In</a></li>' +
        '        <li><a href="signup.html" style="color:#94a3b8;">Create Account</a></li>' +
        '        <li><a href="dashboard.html" style="color:#94a3b8;">User Dashboard</a></li>' +
        '      </ul></div>' +
        '    <div><h4 style="color:#ffffff;margin-top:0;font-family:Montserrat,sans-serif;">Legal &amp; Compliance</h4>' +
        '      <ul style="list-style:none;padding:0;margin:0;line-height:2;">' +
        '        <li><a href="index.html" style="color:#94a3b8;">About Chrysalias.com</a></li>' +
        '        <li><a href="index.html" style="color:#94a3b8;">Government Licenses</a></li>' +
        '      </ul></div>' +
        '  </div>' +
        '  <div style="max-width:1120px;margin:40px auto 0 auto;border-top:1px solid rgba(255,255,255,0.1);padding-top:20px;text-align:center;color:#64748b;">' +
        '    &copy; 2026 Chrysalias.com. All rights reserved.' +
        '  </div>' +
        '</footer>';
    }
  };

  function initStickyHeader() {
    var headerElem = document.querySelector('.chrysalias-nav-header');
    var heroElem = document.querySelector('.sectionHero') || document.querySelector('.hero');
    if (!headerElem) return;
    function onScroll() {
      var heroHeight = heroElem ? (heroElem.offsetHeight || 450) : 400;
      var scrollPos = window.scrollY || window.pageYOffset || 0;
      if (scrollPos > heroHeight) headerElem.classList.add('is-sticky');
      else headerElem.classList.remove('is-sticky');
    }
    window.addEventListener('scroll', onScroll);
    onScroll();
  }

  document.addEventListener('DOMContentLoaded', function () {
    window.EscrowApp.renderHeader();
    window.EscrowApp.renderFooter();
    initStickyHeader();
  });
})();
