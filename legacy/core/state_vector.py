S_object = {
  position: (x0, y0),
  scale: R_core,
  energy: {
    core: E_core,
    profile: E_ring(r)
  },
  flow: {
    profile: J_ring(r),
    curl: curl_sign
  },
  dynamics: {
    omega_E,
    omega_J,
    phase_profile φ(r),
    fluctuation σ_E
  }
}
