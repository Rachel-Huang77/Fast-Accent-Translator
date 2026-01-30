**Frontend Feature-to-Test Mapping**

| Feature / Capability                                             | Main Implementation (Frontend)                                                                 | Automated Tests (Frontend)                                                                                                      | Manual / System Tests                                                                                     |
| ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| Authentication flows (Login / Register / Forgot Password)        | `frontend/src/pages/Login/LoginPage.jsx`; `frontend/src/pages/Register/RegisterPage.jsx`; `frontend/src/pages/ForgotPassword/ForgotPasswordPage.jsx`; `frontend/src/api/auth.js` | `tests/frontend/pages/Login/LoginPage.test.jsx`; `tests/frontend/pages/Register/RegisterPage.test.jsx`; `tests/frontend/pages/ForgotPassword/ForgotPasswordPage.test.jsx`; `tests/frontend/api/auth.test.js` | `TESTING.md` → Scenario **1. Basic Login + Dashboard Access**; Scenario **5. Error Handling (Network/API Failures)** (failed API calls, error banners, validation messages) |
| Main Dashboard: conversation list & switching, start/stop streaming, model/accent selection | `frontend/src/pages/Dashboard/Dashboard.jsx`; `frontend/src/api/conversations.js`; streaming client / WebSocket utility modules | `tests/frontend/pages/Dashboard/Dashboard.test.jsx` (load and display conversations, create/switch active conversation, restoration from local state, invoking streaming client logic and some error paths) | `TESTING.md` → Scenario **1. Basic Login + Dashboard Access** (dashboard loading); Scenario **2. Free Model: Real-time Accent Translation**; Scenario **3. Paid Model: TTS via ElevenLabs**; Scenario **5. Error Handling (Network/API Failures)** |
| Admin UI: user & license key management                          | `frontend/src/pages/Admin/AdminDashboard.jsx`; `AdminUserManagement.jsx`; `AdminKeyManagement.jsx` | `tests/frontend/pages/Admin/AdminDashboard.test.jsx`; `tests/frontend/pages/Admin/AdminUserManagement.test.jsx`; `tests/frontend/pages/Admin/AdminKeyManagement.test.jsx` | `TESTING.md` → Scenario **4. Admin: Role-based Access Control** (403 for non-admins, correct behaviour and UI for admins) |
| API & configuration layer (base URL, HTTP client, error handling) | `frontend/src/config/api.js`; `frontend/src/api/auth.js`; other API modules                     | `tests/frontend/config/api.test.js` (base configuration and error handling); `tests/frontend/api/auth.test.js` (auth-related API wrappers) | All scenarios in `TESTING.md` (1–5) use these API wrappers indirectly; especially Scenario **5. Error Handling (Network/API Failures)** |
| Form validation utilities (email, password rules, etc.)          | `frontend/src/utils/validators.js`                                                              | `tests/frontend/utils/validators.test.js` (validation for various valid and invalid inputs)                                     | Indirectly covered by the Login / Register / Forgot Password page tests; relevant to `TESTING.md` Scenarios **1 / 5** |
| Reusable UI components (e.g., message list / chat bubble)        | `frontend/src/components/MessageBox.jsx` and other shared components                            | `tests/frontend/components/MessageBox.test.jsx` (different message types, rendering order, empty states, styling expectations) | Visual behaviour observed across all manual scenarios; especially `TESTING.md` Scenarios **2 / 3** (displaying translated messages in real time) |

**Frontend – what is covered?**

**Component-level tests**
- Reusable UI components (buttons, forms, layout components)
  - `MessageBox` component (~90% coverage)
  - Form validation and error display components

**Page-level tests**
- Authentication pages (`LoginPage`, `RegisterPage`, `ForgotPasswordPage`)
  - Form rendering and user interactions
  - Form validation and error messaging
  - Navigation and state management
  - Coverage: ~85% for login/register flows
- Admin pages (`AdminDashboard`, `AdminUserManagement`, `AdminKeyManagement`)
  - Rendering and basic management interactions
  - User and license key CRUD operations
  - Role-based access control
  - Coverage: High coverage for admin operations
- Dashboard (`Dashboard`)
  - Start/stop streaming button behaviour
  - Conversation selection and title display
  - Model/accent selector behaviour (state changes)
  - Conversation CRUD operations (create, rename, delete, switch)
  - Coverage: Key logic covered (~70% branches, core interactions tested)

**Utility functions and configuration**
- `utils/validators.js` - Input validation (~95% coverage)
- `config/api.js` - API request handling and error management
- `api/auth.js` - Authentication API functions

**Key coverage areas**
- User login / registration flow (complete flow testing)
- Admin page operations (user management, license key management)
- Dashboard core interactions (start/stop, conversation switching, accent & model selection)

**Test coverage summary**
- **Overall**: Statements ~67.98% , Branches ~85.14%, Functions ~56.16% , Lines ~67.98%
- **api**: ~100% coverage (auth.js - authentication API functions with full test coverage)
- **Components**: ~100% coverage (MessageBox and other shared components)
- **Utils/Config**: ~100% coverage (validators, API configuration)
- **Admin/Login pages**: High coverage (~85-90% for critical paths)
- **Dashboard**: Core logic covered (~70% branches, key interactions tested)

**Why streaming parts are not fully automated**

Real-time audio capture, Web Speech API, MediaRecorder, and raw WebSocket streaming are not fully automated because:

1. **Browser API limitations in CI**
   - Microphone access (`navigator.mediaDevices.getUserMedia`) requires user permission and real hardware
   - Web Speech API (`webkitSpeechRecognition`) is browser-specific and unstable in headless environments
   - MediaRecorder API behavior varies across browsers and CI environments

2. **WebSocket streaming complexity**
   - Real-time audio streaming over WebSockets requires continuous connection and binary data handling
   - Difficult to mock accurately in test environments
   - Timing-dependent behavior is hard to verify programmatically

3. **Our testing approach**
   - **Pure logic is unit tested**: Text processing, TTS request logic, state management
   - **Component behavior is tested**: Button clicks, state changes, UI updates (with mocked WebSocket/APIs)
   - **Browser-dependent parts use manual testing**: Real microphone, Web Speech API, live WebSocket connections
   - **Manual test cases documented**: See "System / End-to-end Testing (Manual)" section below