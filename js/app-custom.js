/**
 * Chrysalias.com Global Unified Engine
 * Clean Production API Integration connected to live PostgreSQL Database
 * No mock data arrays & no local storage dependency
 */

(function () {
  'use strict';

  const isRemote = window.location.hostname.includes('github.io') || window.location.hostname.includes('onrender.com');
  const API_BASE = isRemote 
    ? 'https://chrysalias-backend.onrender.com/api'
    : 'http://127.0.0.1:8000/api';

  window.EscrowApp = {
    API_BASE: API_BASE,

    getUser: function () {
      try {
        const u = sessionStorage.getItem('chrysalias_active_user');
        return u ? JSON.parse(u) : null;
      } catch (e) { return null; }
    },

    setUser: function (userObj) {
      if (!userObj) {
        sessionStorage.removeItem('chrysalias_active_user');
      } else {
        sessionStorage.setItem('chrysalias_active_user', JSON.stringify(userObj));
      }
    },

    logout: function () {
      sessionStorage.removeItem('chrysalias_active_user');
      sessionStorage.removeItem('chrysalias_token');
      try {
        fetch(API_BASE + '/auth/logout/', { method: 'POST' }).catch(function () {});
      } catch (e) {}
      window.location.href = 'login.html';
    },

    getTransactions: function () {
      // Synchronous return from memory/session cache or empty array
      try {
        const txs = sessionStorage.getItem('chrysalias_transactions');
        return txs ? JSON.parse(txs) : [];
      } catch (e) {
        return [];
      }
    },

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

    fetchBackendTransactions: async function () {
      try {
        const resp = await fetch(API_BASE + '/transactions/');
        if (resp.ok) {
          const data = await resp.json();
          if (Array.isArray(data)) {
            const mapped = data.map(tx => ({
              id: tx.tx_id,
              title: tx.title,
              role: tx.initiator_role || 'Buyer',
              counterparty: tx.seller_email_display || tx.buyer_email_display || 'Counterparty',
              amount: parseFloat(tx.amount),
              currency: tx.currency,
              category: tx.category,
              status: tx.status,
              inspectionPeriod: tx.inspection_period,
              date: tx.created_at ? tx.created_at.split('T')[0] : '',
              isPartneredPayment: tx.is_partnered
            }));
            sessionStorage.setItem('chrysalias_transactions', JSON.stringify(mapped));
            return mapped;
          }
        }
      } catch (e) {
        console.log('PostgreSQL API endpoint unreachable.');
      }
      return this.getTransactions();
    },

    addTransaction: async function (newTx) {
      try {
        const resp = await fetch(API_BASE + '/transactions/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title: newTx.title,
            initiator_role: newTx.role || 'Buyer',
            amount: newTx.amount || newTx.price,
            currency: newTx.currency || 'USD',
            category: newTx.category || 'General Merchandise',
            inspection_period: newTx.inspectionDays || newTx.inspectionPeriod || 2,
            buyer_email: newTx.role === 'Seller' ? newTx.sellerEmail : '',
            seller_email: newTx.role === 'Buyer' ? newTx.sellerEmail : '',
            is_partnered: !!newTx.isPartneredPayment,
          })
        });

        if (resp.ok) {
          await this.fetchBackendTransactions();
        }
      } catch (e) {
        console.log('Backend sync error:', e);
      }
    },

    showToast: function (msg) {
      let container = document.querySelector('.toast-container');
      if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        container.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:99999;display:flex;flex-direction:column;gap:10px;pointer-events:none;';
        document.body.appendChild(container);
      }

      const toast = document.createElement('div');
      toast.style.cssText = 'background:#002b49;color:#ffffff;padding:12px 20px;border-radius:8px;font-size:0.88rem;font-weight:600;box-shadow:0 10px 25px rgba(0,0,0,0.2);display:flex;align-items:center;gap:10px;pointer-events:auto;transition:all 0.3s ease;transform:translateY(20px);opacity:0;border-left:4px solid #3cb95d;';
      toast.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#3cb95d" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg><span>' + msg + '</span>';
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

    calculateFees: function (amount) {
      amount = parseFloat(amount) || 0;
      var feeRate = 0.0325;
      if (amount > 25000) feeRate = 0.0125;
      else if (amount > 5000) feeRate = 0.022;
      var escrowFee = Math.max(25, amount * feeRate);
      var processingFee = amount * 0.015;
      return { escrowFee: escrowFee, processingFee: processingFee, totalFee: escrowFee + processingFee };
    },

    // ---------- Header & Navigation Generator ----------
    renderHeader: function (activePage) {
      activePage = activePage || '';
      var headerContainer = document.getElementById('app-header');
      if (!headerContainer) return;

      var path = window.location.pathname.toLowerCase();

      // Suppress header on auth & transaction pages
      if (path.includes('login.html') || path.includes('signup.html') || path.includes('start-transaction.html')) {
        headerContainer.innerHTML = '';
        return;
      }

      var isDashboard = activePage === 'dashboard' || path.includes('dashboard.html');
      var realUser = this.getUser();
      
      // If user is not logged in on dashboard, redirect to login
      if (isDashboard && !realUser) {
        window.location.href = 'login.html';
        return;
      }

      var user = realUser || { name: 'Guest User', email: '' };
      var nameParts = user.name ? user.name.trim().split(' ') : ['User'];
      var initials = nameParts.length > 1
        ? (nameParts[0].charAt(0) + nameParts[nameParts.length - 1].charAt(0)).toUpperCase()
        : nameParts[0].substring(0, 2).toUpperCase();

      if (isDashboard) {
        headerContainer.innerHTML =
          '<header class="dashboard-header-bar">' +
          '  <div class="dashboard-header-container">' +
          '    <a href="index.html" class="dashboard-logo" title="Go to home page" style="display:flex;align-items:center;gap:10px;text-decoration:none;">' +
          '      <img src="build/images/chrysalias-logo-icon.png" alt="Chrysalias" style="height:32px;width:32px;border-radius:6px;object-fit:cover;">' +
          '      <span style="font-family: Montserrat,sans-serif;font-weight:800;font-size:1.45rem;color:#002b49;letter-spacing:-0.5px;">CHRYSALIAS<span style="color:#3cb95d">.COM</span></span>' +
          '    </a>' +
          '    <div class="dashboard-header-right">' +
          '      <div class="dashboard-user-profile-wrapper" id="userProfileBtn">' +
          '        <div class="user-avatar-circle">' + initials + '</div>' +
          '        <span class="user-profile-name">' + user.name + '</span>' +
          '        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg>' +
          '        <div class="user-profile-dropdown" id="userDropdown">' +
          '          <div class="dropdown-user-info"><strong>' + user.name + '</strong><small>' + user.email + '</small></div>' +
          '          <hr>' +
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
          var userBtn = document.getElementById('userProfileBtn');
          var userDd = document.getElementById('userDropdown');
          var logoutBtn = document.getElementById('logoutBtn');

          if (userBtn && userDd) {
            userBtn.addEventListener('click', function (e) {
              e.stopPropagation();
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

      // -------- Public Pages Navigation Header --------
      var authButtons = realUser
        ? '<a href="dashboard.html" class="headerV2-btn headerV2-btn--login">Dashboard (' + realUser.name.split(' ')[0] + ')</a>' +
          '<a href="#" class="headerV2-btn headerV2-btn--signup headerV2-logout-link">Log Out</a>'
        : '<a href="login.html" class="headerV2-btn headerV2-btn--login">Log In</a>' +
          '<a href="signup.html" class="headerV2-btn headerV2-btn--signup">Sign Up</a>';

      headerContainer.innerHTML =
        '<header class="headerV2">' +
        '  <div class="headerV2-topBar">' +
        '    <div class="headerV2-container section-container">' +
        '      <div class="headerV2-topBar-inner">' +
        '        <div class="headerV2-topBar-left">' +
        '          <span>Licensed & Verified Payment Protection Platform</span>' +
        '        </div>' +
        '        <div class="headerV2-topBar-right">' +
        '          <a href="https://chrysalias.com" class="headerV2-supportLink">Chrysalias.com</a>' +
        '        </div>' +
        '      </div>' +
        '    </div>' +
        '  </div>' +
        '  <div class="headerV2-primary">' +
        '    <div class="headerV2-container section-container">' +
        '      <div class="headerV2-inner">' +
        '        <div class="headerV2-logoGroup">' +
        '          <a href="index.html" class="headerV2-logo" title="Go to home page" style="display:flex;align-items:center;gap:10px;text-decoration:none;">' +
        '            <img src="build/images/chrysalias-logo-icon.png" alt="Chrysalias" style="height:34px;width:34px;border-radius:6px;object-fit:cover;">' +
        '            <span style="font-family: Montserrat, sans-serif; font-weight:800; font-size:1.6rem; color:#ffffff; letter-spacing: -0.5px;">CHRYSALIAS<span style="color:#3cb95d">.COM</span></span>' +
        '          </a>' +
        '          <nav class="headerV2-nav">' +
        '            <ul class="headerV2-primaryNav">' +
        '              <li><a href="index.html">What is Chrysalias?</a></li>' +
        '              <li><a href="index.html">Protection Services</a></li>' +
        '              <li><a href="index.html">Chrysalias Accounts</a></li>' +
        '            </ul>' +
        '          </nav>' +
        '        </div>' +
        '        <div class="headerV2-actions">' + authButtons + '</div>' +
        '      </div>' +
        '    </div>' +
        '  </div>' +
        '</header>';

      setTimeout(function () {
        var logoutLinks = headerContainer.querySelectorAll('.headerV2-logout-link');
        logoutLinks.forEach(function (link) {
          link.addEventListener('click', function (e) {
            e.preventDefault();
            window.EscrowApp.logout();
          });
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
        '    <div><h4 style="color:#ffffff;margin-top:0;font-family:Montserrat,sans-serif;">Account & Support</h4>' +
        '      <ul style="list-style:none;padding:0;margin:0;line-height:2;">' +
        '        <li><a href="login.html" style="color:#94a3b8;">Sign In</a></li>' +
        '        <li><a href="signup.html" style="color:#94a3b8;">Create Account</a></li>' +
        '        <li><a href="dashboard.html" style="color:#94a3b8;">User Dashboard</a></li>' +
        '      </ul></div>' +
        '    <div><h4 style="color:#ffffff;margin-top:0;font-family:Montserrat,sans-serif;">Legal & Compliance</h4>' +
        '      <ul style="list-style:none;padding:0;margin:0;line-height:2;">' +
        '        <li><a href="index.html" style="color:#94a3b8;">About Chrysalias.com</a></li>' +
        '        <li><a href="index.html" style="color:#94a3b8;">Government Licenses</a></li>' +
        '      </ul></div>' +
        '  </div>' +
        '  <div style="max-width:1120px;margin:40px auto 0 auto;border-top:1px solid rgba(255,255,255,0.1);padding-top:20px;text-align:center;color:#64748b;">' +
        '    &copy; 2026 Chrysalias.com. All rights reserved. Chrysalias is a licensed payment protection platform.' +
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
      if (scrollPos > heroHeight) {
        headerElem.classList.add('is-sticky');
      } else {
        headerElem.classList.remove('is-sticky');
      }
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
