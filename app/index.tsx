import { Redirect } from 'expo-router';

// The root navigator handles auth gating; this just sends first-load traffic
// into the app group, which redirects to (auth) when signed out.
export default function Index() {
  return <Redirect href="/(tabs)" />;
}
