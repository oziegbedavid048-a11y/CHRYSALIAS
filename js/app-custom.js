/**
 * Chrysalias.com Global Unified Engine & Header/Footer/Sticky Renderer
 * Fixed: renderFooter template literal, all dropdown bindings, tab switching
 */

(function () {
  'use strict';

  const DEFAULT_TRANSACTIONS = [
    {
      id: "ESC-892401",
      title: "Premium Domain Transfer (FintechApp.com)",
      role: "Seller",
      counterparty: "alex.buyer@investments.co",
      amount: 15500.00,
      currency: "USD",
      category: "Domain Names",
      status: "Funded",
      inspectionPeriod: 5,
      date: "2026-07-22"
    },
    {
      id: "ESC-891904",
      title: "2024 Porsche 911 GT3 (VIN: WP0ZZZ99ZLS88912)",
      role: "Buyer",
      counterparty: "motorclassics@dealers.com",
      amount: 178000.00,
      currency: "USD",
      category: "Motor Vehicles",
      status: "In Inspection",
      inspectionPeriod: 3,
      date: "2026-07-20"
    },
    {
      id: "ESC-889021",
      title: "Bulk Electronics Wholesale Shipment",
      role: "Seller",
      counterparty: "techimports.us@gmail.com",
      amount: 4200.00,
      currency: "USD",
      category: "General Goods",
      status: "Completed",
      inspectionPeriod: 7,
      date: "2026-07-10"
    }
  ];

  const API_BASE = 'http://127.0.0.1:8000/api';

  window.EscrowApp = {
    API_BASE: API_BASE,

    getUser: function () {
      try {
        const u = localStorage.getItem('escrow_user');
        return u ? JSON.parse(u) : null;
      } catch (e) { return null; }
    },

    setUser: function (userObj) {
      localStorage.setItem('escrow_user', JSON.stringify(userObj));
    },

    logout: function () {
      localStorage.removeItem('escrow_user');
      localStorage.removeItem('escrow_token');
      // Attempt backend logout
      try {
        fetch(API_BASE + '/auth/logout/', { method: 'POST' }).catch(function () {});
      } catch (e) {}
      window.location.href = 'login.html';
    },

    getTransactions: function () {
      try {
        const txs = localStorage.getItem('escrow_transactions');
        if (!txs) {
          localStorage.setItem('escrow_transactions', JSON.stringify(DEFAULT_TRANSACTIONS));
          return DEFAULT_TRANSACTIONS;
        }
        return JSON.parse(txs);
      } catch (e) {
        return DEFAULT_TRANSACTIONS;
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
          if (Array.isArray(data) && data.length > 0) {
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
              date: tx.created_at ? tx.created_at.split('T')[0] : '2026-07-31',
              isPartneredPayment: tx.is_partnered
            }));
            localStorage.setItem('escrow_transactions', JSON.stringify(mapped));
            return mapped;
          }
        }
      } catch (e) {
        console.log('Django API backend offline or unreachable, using local storage cache.');
      }
      return this.getTransactions();
    },

    addTransaction: function (newTx) {
      const txs = this.getTransactions();
      txs.unshift(newTx);
      localStorage.setItem('escrow_transactions', JSON.stringify(txs));

      // Async post to Django backend if online
      try {
        fetch(API_BASE + '/transactions/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title: newTx.title,
            initiator_role: newTx.role || 'Buyer',
            amount: newTx.amount,
            currency: newTx.currency || 'USD',
            category: newTx.category || 'General Merchandise',
            inspection_period: newTx.inspectionPeriod || 2,
            buyer_email: newTx.counterparty || '',
            seller_email: newTx.counterparty || '',
            is_partnered: !!newTx.isPartneredPayment,
          })
        }).catch(function () {});
      } catch (e) {}
    },

    showToast: function (msg) {
      let container = document.querySelector('.toast-container');
      if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
      }
      const toast = document.createElement('div');
      toast.className = 'toast';
      toast.innerHTML = '<span>' + msg + '</span>';
      container.appendChild(toast);
      setTimeout(function () {
        toast.style.opacity = '0';
        setTimeout(function () { toast.remove(); }, 300);
      }, 3500);
    },

    calculateFee: function (amount) {
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
      var user = realUser || { name: 'Alex Mercer', email: 'alex.seller@chrysalias-demo.com' };
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
          '      <div class="dashboard-notif-wrapper">' +
          '        <button type="button" class="dashboard-notif-btn" id="notifBellBtn" title="Notifications">' +
          '          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
          '            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>' +
          '            <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>' +
          '          </svg>' +
          '          <span class="notif-badge" id="notifBadge">2</span>' +
          '        </button>' +
          '        <div class="notif-dropdown" id="notifDropdown">' +
          '          <div class="notif-dropdown-header">' +
          '            <strong>Notifications</strong>' +
          '            <span class="mark-read" id="markReadBtn">Mark all read</span>' +
          '          </div>' +
          '          <div class="notif-item">' +
          '            <div class="notif-dot"></div>' +
          '            <div><p class="notif-title">Transaction ESC-892401 Funded</p><span class="notif-time">10 mins ago</span></div>' +
          '          </div>' +
          '          <div class="notif-item">' +
          '            <div class="notif-dot"></div>' +
          '            <div><p class="notif-title">Identity Verification Approved</p><span class="notif-time">1 hour ago</span></div>' +
          '          </div>' +
          '        </div>' +
          '      </div>' +
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

        // Bind all dropdown interactions after DOM injection
        setTimeout(function () {
          var bellBtn = document.getElementById('notifBellBtn');
          var notifDd = document.getElementById('notifDropdown');
          var userBtn = document.getElementById('userProfileBtn');
          var userDd = document.getElementById('userDropdown');
          var markReadBtn = document.getElementById('markReadBtn');
          var logoutBtn = document.getElementById('logoutBtn');
          var notifBadge = document.getElementById('notifBadge');

          if (bellBtn && notifDd) {
            bellBtn.addEventListener('click', function (e) {
              e.stopPropagation();
              if (userDd) userDd.classList.remove('show');
              notifDd.classList.toggle('show');
            });
          }

          if (userBtn && userDd) {
            userBtn.addEventListener('click', function (e) {
              e.stopPropagation();
              if (notifDd) notifDd.classList.remove('show');
              userDd.classList.toggle('show');
            });
          }

          if (markReadBtn && notifBadge) {
            markReadBtn.addEventListener('click', function (e) {
              e.stopPropagation();
              notifBadge.style.display = 'none';
              window.EscrowApp.showToast('All notifications marked as read.');
              if (notifDd) notifDd.classList.remove('show');
            });
          }

          if (logoutBtn) {
            logoutBtn.addEventListener('click', function (e) {
              e.preventDefault();
              window.EscrowApp.logout();
            });
          }

          document.addEventListener('click', function () {
            if (notifDd) notifDd.classList.remove('show');
            if (userDd) userDd.classList.remove('show');
          });
        }, 50);

        return;
      }

      // -------- Public Pages Navigation Header --------
      var authHtml = realUser && realUser.name
        ? '<li class="headerV2-authNav-item"><a href="dashboard.html" class="headerV2-authNav-link" style="font-weight:700;color:#3cb95d;"><span class="headerV2-authNav-text">My Dashboard (' + realUser.name.split(' ')[0] + ')</span></a></li>' +
          '<li class="headerV2-authNav-item"><a href="#" class="headerV2-authNav-link headerV2-logout-link"><span class="headerV2-authNav-text" style="opacity:0.8;">Logout</span></a></li>'
        : '<li class="headerV2-authNav-item"><a href="login.html" class="headerV2-authNav-link"><span class="headerV2-authNav-text">Login</span></a></li>' +
          '<li class="headerV2-authNav-item"><a href="signup.html" class="headerV2-authNav-link"><span class="headerV2-authNav-text">Signup</span></a></li>';

      headerContainer.innerHTML =
        '<div class="chrysalias-nav-header">' +
        '  <header class="headerV2 is-header-scrollTop">' +
        '    <div class="headerV2-primary">' +
        '      <div class="headerV2-container section-container">' +
        '        <div class="headerV2-inner">' +
        '          <a href="index.html" class="headerV2-logo" title="Go to home page" style="display:flex;align-items:center;gap:10px;text-decoration:none;">' +
        '            <img src="build/images/chrysalias-logo-icon.png" alt="Chrysalias" style="height:34px;width:34px;border-radius:6px;object-fit:cover;">' +
        '            <span style="font-family: Montserrat, sans-serif; font-weight:800; font-size:1.6rem; color:#ffffff; letter-spacing: -0.5px;">CHRYSALIAS<span style="color:#3cb95d">.COM</span></span>' +
        '          </a>' +
        '          <nav class="headerV2-nav">' +
        '            <ul class="headerV2-primaryNav">' +
        '              <li class="headerV2-primaryNav-item" data-header-nav-item="">' +
        '                <span class="headerV2-primaryNav-title"><span class="headerV2-primaryNav-text">Consumer</span></span>' +
        '                <div class="headerV2-subnav"><ul class="headerV2-subnav-list">' +
        '                  <li class="headerV2-subnav-item"><a href="index.html" class="headerV2-subnav-link"><h3 class="headerV2-subnav-title">What is Chrysalias?</h3><p class="headerV2-subnav-desc">Learn how payments are protected</p></a></li>' +
        '                  <li class="headerV2-subnav-item"><a href="index.html" class="headerV2-subnav-link"><h3 class="headerV2-subnav-title">Domain Names</h3><p class="headerV2-subnav-desc">Domain concierge protection</p></a></li>' +
        '                  <li class="headerV2-subnav-item"><a href="index.html" class="headerV2-subnav-link"><h3 class="headerV2-subnav-title">Motor Vehicles</h3><p class="headerV2-subnav-desc">Cars, boats, and VIN checks</p></a></li>' +
        '                  <li class="headerV2-subnav-item"><a href="index.html" class="headerV2-subnav-link"><h3 class="headerV2-subnav-title">General Merchandise</h3><p class="headerV2-subnav-desc">Luxury goods & art</p></a></li>' +
        '                </ul></div>' +
        '              </li>' +
        '              <li class="headerV2-primaryNav-item" data-header-nav-item="">' +
        '                <span class="headerV2-primaryNav-title"><span class="headerV2-primaryNav-text">Broker</span></span>' +
        '                <div class="headerV2-subnav"><ul class="headerV2-subnav-list">' +
        '                  <li class="headerV2-subnav-item"><a href="index.html" class="headerV2-subnav-link"><h3 class="headerV2-subnav-title">Brokerage Services</h3><p class="headerV2-subnav-desc">Domain & broker commissions</p></a></li>' +
        '                  <li class="headerV2-subnav-item"><a href="index.html" class="headerV2-subnav-link"><h3 class="headerV2-subnav-title">Domain Holding</h3><p class="headerV2-subnav-desc">Long-term DNS & ICANN holding</p></a></li>' +
        '                </ul></div>' +
        '              </li>' +
        '              <li class="headerV2-primaryNav-item" data-header-nav-item="">' +
        '                <span class="headerV2-primaryNav-title"><span class="headerV2-primaryNav-text">Business</span></span>' +
        '                <div class="headerV2-subnav"><ul class="headerV2-subnav-list">' +
        '                  <li class="headerV2-subnav-item"><a href="index.html" class="headerV2-subnav-link"><h3 class="headerV2-subnav-title">E-Commerce Checkout</h3><p class="headerV2-subnav-desc">Marketplace integrations</p></a></li>' +
        '                  <li class="headerV2-subnav-item"><a href="index.html" class="headerV2-subnav-link"><h3 class="headerV2-subnav-title">Digital Letter of Credit</h3><p class="headerV2-subnav-desc">Global B2B trade protection</p></a></li>' +
        '                </ul></div>' +
        '              </li>' +
        '              <li class="headerV2-primaryNav-item" data-header-nav-item="">' +
        '                <span class="headerV2-primaryNav-title"><span class="headerV2-primaryNav-text">Help</span></span>' +
        '                <div class="headerV2-subnav"><ul class="headerV2-subnav-list">' +
        '                  <li class="headerV2-subnav-item"><a href="index.html" class="headerV2-subnav-link"><h3 class="headerV2-subnav-title">Help Desk / FAQs</h3><p class="headerV2-subnav-desc">Search common answers</p></a></li>' +
        '                  <li class="headerV2-subnav-item"><a href="index.html" class="headerV2-subnav-link"><h3 class="headerV2-subnav-title">About Us</h3><p class="headerV2-subnav-desc">Over 25 years of trust</p></a></li>' +
        '                </ul></div>' +
        '              </li>' +
        '            </ul>' +
        '            <ul class="headerV2-authNav">' + authHtml + '</ul>' +
        '          </nav>' +
        '        </div>' +
        '      </div>' +
        '    </div>' +
        '  </header>' +
        '</div>';

      // Bind logout for public nav
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

  // ---------- Sticky Header on scroll (index.html) ----------
  function initStickyHeader() {
    var headerElem = document.querySelector('.chrysalias-nav-header');
    var heroElem = document.querySelector('.sectionHero') || document.querySelector('.hero');
    if (!headerElem) return;

    function onScroll() {
      var heroHeight = heroElem ? (heroElem.offsetHeight || 450) : 400;
      var scrollPos = window.scrollY || window.pageYOffset || 0;

      if (scrollPos > (heroHeight - 90)) {
        headerElem.classList.add('is-sticky-header');
      } else {
        headerElem.classList.remove('is-sticky-header');
      }
    }

    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  document.addEventListener('DOMContentLoaded', function () {
    window.EscrowApp.renderHeader();
    window.EscrowApp.renderFooter();
    initStickyHeader();
  });

})();
