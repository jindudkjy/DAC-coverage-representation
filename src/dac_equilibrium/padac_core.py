# fidelity_core.py — helpers for the process-level equilibrium-information fidelity notebook.
# Written by Section 0. Contains NO analysis state: all state lives in RUN_DIR/_state and
# is reloaded explicitly by each section (no hidden notebook state).
#
# Interpretation constraint (Section 46, repeated here on purpose):
#   H = equilibrium-side environmental opportunity descriptor;  Y = controller/process outcome.
#   IRA environmental loading release is NOT recovered CO2.
#   PADAC (field-tested with Zeolite 13X) + ImCOF (adsorption/TPD measured independently)
#   is a literature-constrained MODEL COMPOSITION, not an experimentally validated ImCOF reactor.
import os, re, ast, json, hashlib, pickle, inspect, itertools, datetime as _dt
import numpy as np
import pandas as pd

PROVENANCE_CLASSES = (
    "DIRECT_REPORTED_MEASURED", "DIRECT_REPORTED_DESIGN", "DIGITIZED_FROM_FIGURE",
    "LITERATURE_PARAMETER", "FITTED_BY_SOURCE_AUTHORS", "DERIVED_FROM_REPORTED_EQUATION",
    "CALCULATED_THIS_NOTEBOOK", "ASSUMED_SENSITIVITY_PARAMETER", "REANALYSIS_DATA", "NASA_POWER_API", "NOT_AVAILABLE")
OK_PREFIXES = ("EXECUTED", "PASSED", "STRUCTURAL_REPRODUCTION_ONLY",
               "FIELD_TRACE_NOT_EXACTLY_REPRODUCIBLE_FROM_AVAILABLE_INPUT")
SESSION_PATH = "/content/fidelity_session.json"
CONFIG_PATH = "/content/fidelity_config.json"


class HardStop(Exception):
    """Raised when a gate fails. Callers record NOT_EXECUTED_<REASON> and continue other branches."""


# ----------------------------------------------------------------------------- session / state
def now():
    return _dt.datetime.now().isoformat(timespec="seconds")


def load_config():
    if not os.path.exists(CONFIG_PATH):
        raise HardStop("Config missing: run Section 0.")
    with open(CONFIG_PATH) as f:
        return json.load(f)


def load_session():
    if not os.path.exists(SESSION_PATH):
        raise HardStop("Session missing: run Sections 0–2.")
    with open(SESSION_PATH) as f:
        return json.load(f)


def update_session(**kw):
    s = {}
    if os.path.exists(SESSION_PATH):
        with open(SESSION_PATH) as f:
            s = json.load(f)
    s.update(kw)
    with open(SESSION_PATH, "w") as f:
        json.dump(s, f, indent=2, default=str)
    if s.get("RUN_DIR"):   # mirror into the run so a Colab restart can recover it
        os.makedirs(s["RUN_DIR"], exist_ok=True)
        with open(os.path.join(s["RUN_DIR"], "session.json"), "w") as f:
            json.dump(s, f, indent=2, default=str)
    return s


def run_dir():
    return load_session()["RUN_DIR"]


def _state_dir():
    d = os.path.join(run_dir(), "_state")
    os.makedirs(d, exist_ok=True)
    return d


_MISSING = object()


def put(name, obj):
    with open(os.path.join(_state_dir(), name + ".pkl"), "wb") as f:
        pickle.dump(obj, f)


def get(name, default=_MISSING):
    p = os.path.join(_state_dir(), name + ".pkl")
    if not os.path.exists(p):
        if default is _MISSING:
            raise HardStop(f"State '{name}' not found — rerun the section that produces it.")
        return default
    with open(p, "rb") as f:
        return pickle.load(f)


def _jsonl_append(fname, rec):
    with open(os.path.join(_state_dir(), fname), "a") as f:
        f.write(json.dumps(rec, default=str) + "\n")


def _jsonl_read(fname):
    p = os.path.join(_state_dir(), fname)
    if not os.path.exists(p):
        return []
    with open(p) as f:
        return [json.loads(l) for l in f if l.strip()]


def warn(code, message, section):
    _jsonl_append("warnings.jsonl", dict(time=now(), section=section, code=code, message=message))
    print(f"[WARN {code}] {message}")


def set_status(branch, status, reason="", section=""):
    _jsonl_append("eligibility.jsonl",
                  dict(time=now(), branch=branch, status=status, reason=reason, section=section))
    print(f"[STATUS] {branch}: {status} {('— ' + reason) if reason else ''}")


def not_executed(branch, reason_code, detail, section):
    set_status(branch, f"NOT_EXECUTED_{reason_code}", detail, section)


def statuses():
    latest = {}
    for r in _jsonl_read("eligibility.jsonl"):
        latest[r["branch"]] = r
    return latest


def status_of(branch):
    return statuses().get(branch, {}).get("status", "NOT_RUN")


def is_ok(*branches):
    return all(status_of(b).startswith(OK_PREFIXES) for b in branches)


def record_assumption(name, value, provenance, rationale, section, branch=""):
    if provenance not in PROVENANCE_CLASSES:
        raise ValueError(f"Unknown provenance class {provenance}")
    _jsonl_append("assumptions.jsonl", dict(time=now(), section=section, branch=branch, name=name,
                                            value=value, provenance=provenance, rationale=rationale))


def save_csv(df, name):
    p = os.path.join(run_dir(), name)
    df.to_csv(p, index=False)
    print("saved", p, f"({len(df)} rows)")
    return p


def guarded(branch, section, fn):
    """Run fn(); on HardStop record NOT_EXECUTED and return None instead of crashing other branches."""
    try:
        return fn()
    except HardStop as e:
        msg = str(e)
        code = msg.split(":")[0] if msg.split(":")[0].isupper() else "HARD_STOP"
        not_executed(branch, code, msg, section)
        return None


# ----------------------------------------------------------------------------- files / provenance
def drive_id(path):
    for attr in ("user.drive.id", "user.drive.item_id", "user.drive.itemprotostr"):
        try:
            v = os.getxattr(path, attr).decode(errors="ignore")
            m = re.search(r"[A-Za-z0-9_-]{20,}", v)
            return m.group(0) if m else v
        except Exception:
            pass
    return None


_DRIVE_PLACEHOLDER_EXTS = {".gsheet", ".gdoc", ".gslides", ".gdraw", ".gform", ".gmap", ".gsite"}


def _drive_placeholder(path):
    """True for Colab/Drive FUSE locator files that are not normal byte streams."""
    return os.path.splitext(str(path))[1].lower() in _DRIVE_PLACEHOLDER_EXTS


def sha256(path, chunk=1 << 20, max_bytes=5 * 1024 ** 3):
    """Hash ordinary byte-backed files; never crash on Google Workspace placeholders.

    Google Drive mounted .gsheet/.gdoc/.gslides entries are locators, not the
    underlying Workspace document bytes. Their content hash is therefore not a
    meaningful file SHA256. Other FUSE read failures are recorded explicitly
    rather than aborting the scientific pipeline.
    """
    if _drive_placeholder(path):
        return "GOOGLE_DRIVE_PLACEHOLDER_UNHASHED"
    try:
        if os.path.getsize(path) > max_bytes:
            return "SKIPPED_FILE_TOO_LARGE"
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for b in iter(lambda: f.read(chunk), b""):
                h.update(b)
        return h.hexdigest()
    except OSError as e:
        # Drive FUSE can expose metadata for cloud-native files while rejecting
        # POSIX byte reads (e.g. Errno 95 Operation not supported). Preserve the
        # locator/provenance record and make the missing byte hash explicit.
        return f"UNHASHED_OSERROR_{getattr(e, 'errno', 'UNKNOWN')}"


def register_input(path, provenance, role, section, source_id=None, note=""):
    if provenance not in PROVENANCE_CLASSES + ("CODE_NON_NUMERIC", "AUDIT_ONLY"):
        raise ValueError(provenance)
    try:
        st = os.stat(path)
        size_bytes = st.st_size
        mtime = _dt.datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds")
    except OSError as e:
        size_bytes = None
        mtime = None
        note = (note + "; " if note else "") + f"stat unavailable: OSError errno={getattr(e, 'errno', None)}"
    if os.path.isdir(path):
        digest = "DIRECTORY"
    else:
        digest = sha256(path)
    if _drive_placeholder(path):
        note = (note + "; " if note else "") + "Google Workspace Drive placeholder; locator registered, underlying cloud document bytes not hashed"
    rec = dict(path=os.path.abspath(path), filename=os.path.basename(path),
               drive_id=source_id or drive_id(path), size_bytes=size_bytes,
               mtime=mtime, sha256=digest,
               provenance=provenance, role=role, section=section, note=note)
    _jsonl_append("inputs.jsonl", rec)
    return rec


def walk_find(roots, name_regex, dirs=False, skip_regex=r"(^|/)\.|/_state(/|$)"):
    rx = re.compile(name_regex, re.I)
    sk = re.compile(skip_regex)
    out = []
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dp, dns, fns in os.walk(root):
            if sk.search(dp):
                dns[:] = []
                continue
            for n in (dns if dirs else fns):
                if rx.search(n):
                    out.append(os.path.join(dp, n))
    return sorted(set(out))


# ----------------------------------------------------------------------------- reuse repository code
def load_code_defs(path, extra_globals=None):
    """Import definitions (imports, functions, classes, literal constants) from a repository .py/.ipynb
    WITHOUT executing its top-level pipeline. Cells that fail to parse are skipped and reported."""
    if path.endswith(".ipynb"):
        with open(path) as f:
            nb = json.load(f)
        chunks = ["".join(c["source"]) if isinstance(c["source"], list) else c["source"]
                  for c in nb["cells"] if c["cell_type"] == "code"]
    else:
        with open(path) as f:
            chunks = [f.read()]
    ns = {"__name__": "repo_" + re.sub(r"\W", "_", os.path.basename(path))}
    ns.update(extra_globals or {})
    skipped = []
    for i, src in enumerate(chunks):
        src = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith(("%", "!")))
        try:
            tree = ast.parse(src)
        except SyntaxError as e:
            skipped.append((i, f"SyntaxError: {e}"))
            continue
        keep = []
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef,
                                 ast.AsyncFunctionDef, ast.ClassDef)):
                keep.append(node)
            elif isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
                try:
                    ast.literal_eval(node.value)
                    keep.append(node)
                except Exception:
                    pass
        try:
            exec(compile(ast.Module(body=keep, type_ignores=[]), f"{path}#cell{i}", "exec"), ns)
        except Exception as e:
            skipped.append((i, f"{type(e).__name__}: {e}"))
    ns["__skipped_cells__"] = skipped
    return ns


def list_defs(ns):
    rows = []
    for k, v in ns.items():
        if k.startswith("_") or not callable(v) or getattr(v, "__module__", "") not in (ns.get("__name__"), None):
            continue
        try:
            sig = str(inspect.signature(v))
        except Exception:
            sig = "?"
        doc = (inspect.getdoc(v) or "").split("\n")[0][:120]
        rows.append(dict(name=k, signature=sig, doc=doc))
    return pd.DataFrame(rows)


def detect_col(df, patterns, what, required=True):
    hits = [c for c in df.columns if any(re.search(p, str(c), re.I) for p in patterns)]
    if len(hits) == 1:
        return hits[0]
    if required:
        raise HardStop(f"AMBIGUOUS_COLUMN: {what}: candidates={hits} in {list(df.columns)} — set it in CONFIG.")
    return None


# ----------------------------------------------------------------------------- fidelity metrics
def fidelity(Y_rep, Y_full, label=""):
    """Kendall tau-b / Spearman rho between climate rankings, plus every pairwise reversal."""
    from scipy.stats import kendalltau, spearmanr
    a = pd.Series(Y_rep, dtype=float)
    b = pd.Series(Y_full, dtype=float)
    if set(a.index) != set(b.index):
        raise HardStop(f"CLIMATE_MISMATCH: {label}: rep vs full climates differ.")
    a = a.loc[b.index]
    if a.isna().any() or b.isna().any():
        raise HardStop(f"NAN_SCORE: {label}: NaN in Y; climates={list(a.index[a.isna()]) + list(b.index[b.isna()])}")
    import warnings
    degenerate = bool(a.nunique() < 2 or b.nunique() < 2)   # constant Y: tau/rho undefined (NaN), reported as such
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        tau, ptau = kendalltau(a.values, b.values)
        rho, prho = spearmanr(a.values, b.values)
    pairs = []
    cl = list(b.index)
    for i, j in itertools.combinations(range(len(cl)), 2):
        sf = np.sign(b.iloc[i] - b.iloc[j])
        sr = np.sign(a.iloc[i] - a.iloc[j])
        if sf != sr:
            pairs.append(dict(climate_i=cl[i], climate_j=cl[j], sign_full=int(sf), sign_rep=int(sr),
                              kind="STRICT_REVERSAL" if sf * sr < 0 else "TIE_CHANGE",
                              Y_full_i=b.iloc[i], Y_full_j=b.iloc[j], Y_rep_i=a.iloc[i], Y_rep_j=a.iloc[j]))
    n_pairs = len(cl) * (len(cl) - 1) // 2
    strict = sum(p["kind"] == "STRICT_REVERSAL" for p in pairs)
    rel = (a - b) / b.abs().where(b.abs() > 0)
    finite = rel[np.isfinite(rel)]
    summ = dict(n_climates=len(cl), degenerate_constant_Y=degenerate, kendall_tau_b=tau, kendall_p=ptau, spearman_rho=rho, spearman_p=prho,
                n_pairs=n_pairs, n_strict_reversals=strict, n_tie_changes=len(pairs) - strict,
                reversal_fraction=strict / n_pairs if n_pairs else np.nan,
                mean_abs_rel_error=float(np.abs(finite).mean()) if len(finite) else np.nan,
                max_abs_rel_error=float(np.abs(finite).max()) if len(finite) else np.nan)
    climate_err = pd.DataFrame(dict(climate=cl, Y_full=b.values, Y_rep=a.values,
                                    abs_error=(a - b).values, rel_error=rel.values,
                                    rank_full=b.rank(ascending=False).values,
                                    rank_rep=a.rank(ascending=False).values))
    return summ, pd.DataFrame(pairs), climate_err


# ----------------------------------------------------------------------------- kernels
def monotone_fraction(x, y):
    """Sort by x, enforce non-decreasing y in [0,1]; return x, y, number of corrected points."""
    o = np.argsort(x)
    x, y = np.asarray(x, float)[o], np.asarray(y, float)[o]
    ym = np.clip(np.maximum.accumulate(y), 0, 1)
    return x, ym, int(np.sum(np.abs(ym - np.clip(y, 0, 1)) > 1e-12))


def pseudotime_step(frac_now, dt, k_t, k_F):
    """Advance fractional approach along a measured step-response kernel F(t) by dt using
    equivalent elapsed time (no rate equation is introduced; kernel is used as measured)."""
    t_eq = np.interp(np.clip(frac_now, k_F[0], k_F[-1]), k_F, k_t)
    return float(np.interp(t_eq + dt, k_t, k_F))


# ----------------------------------------------------------------------------- PADAC thermal model
SIGMA = 5.670374419e-8
R_GAS = 8.314462618


def air_props(T_K, P=101325.0):
    """Dry-air properties (ideal gas; Sutherland viscosity; power-law conductivity). LITERATURE_PARAMETER."""
    rho = P * 0.0289647 / (R_GAS * T_K)
    cp = 1006.0 + 0.0 * T_K
    mu = 1.716e-5 * (T_K / 273.15) ** 1.5 * (273.15 + 110.4) / (T_K + 110.4)
    k = 0.0241 * (T_K / 273.15) ** 0.81
    return rho, cp, mu, k


def _ev(expr, env):
    return eval(expr, {"np": np, "__builtins__": {}}, env)


class Forcing:
    """Hourly forcing -> continuous functions of t [s]. Linear interpolation between hourly samples."""
    def __init__(self, t_s, Tamb_K, G, v, flow_on):
        self.t = np.asarray(t_s, float)
        self.Ta, self.G, self.v = (np.asarray(a, float) for a in (Tamb_K, G, v))
        self.flow = np.asarray(flow_on, bool)
        if np.any(np.isnan(self.Ta)) or np.any(np.isnan(self.G)) or np.any(np.isnan(self.v)):
            raise HardStop("FORCING_NAN: forcing contains NaN; no gap filling is performed.")

    def at(self, t):
        return (np.interp(t, self.t, self.Ta), np.interp(t, self.t, self.G), np.interp(t, self.t, self.v))

    def flow_at(self, t):
        """Right-continuous hourly flow schedule: flow[i] applies on [t_i, t_{i+1}).
        This preserves the original hourly schedule exactly; only solver orchestration changes."""
        i = int(np.searchsorted(self.t, float(t), side="right") - 1)
        i = min(max(i, 0), len(self.flow) - 1)
        return bool(self.flow[i])

    def segments(self):
        """Contiguous constant-flow segments (integrated separately: flow switches are discontinuities)."""
        idx = np.flatnonzero(np.diff(self.flow.astype(int))) + 1
        bounds = np.r_[0, idx, len(self.t) - 1]
        return [(self.t[a], self.t[b], bool(self.flow[a])) for a, b in zip(bounds[:-1], bounds[1:]) if b > a]


class PadacModel:
    """Method-of-lines PADAC model (Filahi et al., ECM 338 (2025) 119925, Eqs. 6–15).
    Unknowns per axial node i: T_v (glass), T_w (wall), T_g (gas), T_s (solid) [K], and q [mol/kg]
    when sorption is coupled. Finite-volume axial discretisation; stiff BDF integration.
    Terms whose printed form must be checked against the PDF are taken from P['form'] (string expressions)."""

    def __init__(self, P, nz=20, sorption=None):
        self.P, self.nz = P, nz
        r, s, f = P["reactor"], P["sorbent"], P["form"]
        self.r, self.s, self.f = r, s, f
        self.dz = r["L"] / nz
        self.A = np.pi * r["D_int"] ** 2 / 4
        geo = dict(D_int=r["D_int"], D_ext=r["D_ext"], e_v=r["e_v"], e_w=r["e_w"], L=r["L"], np=np)
        self.a_v = _ev(f["a_v"], geo)
        self.w_solar = _ev(f["wall_solar_factor"], geo)
        self.w_rad = _ev(f["wall_rad_factor"], geo)
        self.w_gas = _ev(f["wall_gas_factor"], geo)
        self.g_wall = _ev(f["gas_wall_factor"], geo)
        self.sorption = sorption   # None | callable(Ts_K, q, flow_on) -> dq/dt [mol/kg/s]
        # Formulation A for ImCOF: desorption heat expressed through the SAME empirical F_R pathway
        # (apparent heat capacity, applied only while the bed heats) -> no second desorption pathway.
        self.apparent_cap = None   # None | callable(Ts_K, t_s) -> extra J m^-3 K^-1
        self.nstate = 5 if sorption else 4

    # --- correlations (forms selectable; primary = Watmuff) ---
    def h_wind(self, v):
        c = self.f["wind_correlation"]
        if c == "watmuff":
            return 2.8 + 3.0 * v
        if c == "kumar":
            return 10.03 + 4.687 * v
        if c == "mcadams_low":
            return 5.7 + 3.8 * v
        if c == "table3_constant":
            return 23.8 + 0.0 * v
        raise HardStop(f"UNKNOWN_WIND_CORRELATION: {c}")

    def coeffs(self, Tg, u):
        """h_w, lambda_gz, h_gs: Table-3 fitted constants or Eqs. 11/13/14 evaluated locally."""
        r, s = self.r, self.s
        rho, cp, mu, k = air_props(Tg)
        Pr = cp * mu / k
        if self.f["coefficient_mode"] == "table3_fitted":
            return (r["h_w_fitted"] + 0 * Tg, r["lambda_gz_fitted"] + 0 * Tg, s["h_gs"] + 0 * Tg)
        Re_D = rho * abs(u) * r["D_int"] / mu
        Re_p = rho * abs(u) * s["d_p"] / mu
        h_w = (12.5 + 0.048 * Re_D) * k / r["D_int"]                       # Eq. 11
        lam = (7.0 + 0.5 * Pr * Re_p) * k                                   # Eq. 13 (Re basis: PDF check)
        h_gs = (2.0 + 1.1 * Pr ** 0.33 * Re_p ** 0.6) * k / s["d_p"]        # Eq. 14 (2R_p = d_p)
        return h_w, lam, h_gs

    def rhs(self, t, y, F, flow_on):
        n, r, s, f = self.nz, self.r, self.s, self.f
        Tv, Tw, Tg, Ts = y[:n], y[n:2 * n], y[2 * n:3 * n], y[3 * n:4 * n]
        Ta, G, v = F.at(t)
        G = G * r.get("G_to_reactor_factor", 1.0)
        Tsky = r["sky_coeff"] * Ta ** 1.5                                   # Eq. 7, absolute temperature [K]
        hw = self.h_wind(v)
        h_vsky = r["eps_v"] * SIGMA * (Tv ** 2 + Tsky ** 2) * (Tv + Tsky)   # Eq. 8
        h_wv = SIGMA * (Tv ** 2 + Tw ** 2) * (Tv + Tw) / (1 / r["eps_v"] + 1 / r["eps_w"] - 1)  # Eq. 9
        glass_wall = (Tw - Tv) if f["eq6_glass_wall_sign"] == "physical" else (Tv - Tw)
        dTv = (self.a_v * r["alpha_v"] * G + self.a_v * h_wv * glass_wall
               - hw * self.a_v * (Tv - Ta) - h_vsky * self.a_v * (Tv - Tsky)) / (r["rho_v"] * r["C_v"])  # Eq. 6

        u = (r["Q_m3_h"] / 3600.0 / self.A) if flow_on else 0.0           # superficial velocity
        h_w, lam, h_gs = self.coeffs(Tg, u)
        dTw = (self.w_solar * r["alpha_w"] * r["tau_g"] * G + self.w_rad * h_wv * (Tv - Tw)
               + self.w_gas * h_w * (Tg - Tw)) / (r["rho_w"] * r["C_w"])  # Eq. 10 (factors: PDF check)

        rho_g, cp, _, _ = air_props(Tg)
        eps, dz = s["eps_bed"], self.dz
        T_in = Ta                                                          # inlet air = ambient
        rho_in, cp_in, _, _ = air_props(np.asarray(T_in, float))
        adv_faces = np.r_[rho_in * cp_in * u, rho_g * cp * u]             # upwind: face 0 = inlet, face i+1 = node i
        F_adv = adv_faces * np.r_[T_in, Tg]                                # faces 0..n
        lam_f = 0.5 * (lam[:-1] + lam[1:])
        F_disp = np.r_[0.0, -lam_f * np.diff(Tg) / dz, 0.0]               # Danckwerts-equivalent in FV
        F_tot = F_adv + F_disp
        q_gs = 6.0 * h_gs / s["d_p"] * (Tg - Ts)                            # Eq. 14/15 volumetric exchange
        dTg = (-(F_tot[1:] - F_tot[:-1]) / dz - f["gas_solid_sign_factor"] * q_gs
               - self.g_wall * h_w * (Tg - Tw)) / (eps * rho_g * cp)       # Eq. 12 (form: PDF check)

        k_s = s["k_s"]
        F_cond = np.r_[0.0, -k_s * np.diff(Ts) / dz, 0.0]                  # adiabatic solid ends
        heat = 0.0
        dq = None
        if self.sorption is not None:
            q = y[4 * n:5 * n]
            dq = self.sorption(Ts, q, flow_on)
            heat = (1 - eps) * s["rho_s"] * s["minus_dH_J_mol"] * dq       # Eq. 15 source term
        cap = (1 - eps) * s["rho_s"] * s["C_s"]
        net = -(F_cond[1:] - F_cond[:-1]) / dz + q_gs + heat
        dTs = net / cap                                                    # Eq. 15
        if self.apparent_cap is not None:
            heating = dTs > 0
            dTs = np.where(heating, net / (cap + self.apparent_cap(Ts, t)), dTs)
        out = [dTv, dTw, dTg, dTs] + ([dq] if dq is not None else [])
        return np.concatenate(out)

    def sparsity(self):
        from scipy.sparse import lil_matrix
        n, m = self.nz, self.nstate
        S = lil_matrix((m * n, m * n), dtype=int)
        V, W, Gg, Sx, Q = (k * n for k in range(5))
        for i in range(n):
            for a, b in [(V, V), (V, W), (W, V), (W, W), (W, Gg), (Gg, Gg), (Gg, W), (Gg, Sx), (Sx, Sx), (Sx, Gg)]:
                S[a + i, b + i] = 1
            for d in (-1, 1):
                if 0 <= i + d < n:
                    S[Gg + i, Gg + i + d] = 1
                    S[Sx + i, Sx + i + d] = 1
            if m == 5:
                for a, b in [(Q, Q), (Q, Sx), (Sx, Q)]:
                    S[a + i, b + i] = 1
        return S

    def _initial_state(self, F, q0=None):
        n = self.nz
        y = np.full(4 * n, F.Ta[0])
        if self.sorption is not None:
            y = np.r_[y, np.full(n, 0.0 if q0 is None else q0)]
        return y

    def _reduce_solution(self, t, Y):
        """Reduce node states to the same hourly outputs used by the legacy implementation."""
        n = self.nz
        res = pd.DataFrame(dict(t_s=np.asarray(t, float)))
        for k, nm in enumerate(["T_v", "T_w", "T_g", "T_s"]):
            blk = Y[k * n:(k + 1) * n, :].T - 273.15
            res[nm + "_mean_C"] = blk.mean(1)
            res[nm + "_max_C"] = blk.max(1)
        res["T_s_mid_C"] = Y[3 * n + n // 2, :] - 273.15
        if self.sorption is not None:
            res["q_mean_mol_kg"] = Y[4 * n:5 * n, :].mean(0)
        return res

    def run(self, F, q0=None, rtol=1e-5, atol=1e-4, extra_heat=None):
        """Legacy segmented BDF reference implementation. Kept unchanged as the regression oracle."""
        from scipy.integrate import solve_ivp
        y = self._initial_state(F, q0)
        S = self.sparsity()
        ts, ys = [F.t[0]], [y.copy()]
        for t0, t1, flow in F.segments():
            te = F.t[(F.t > t0) & (F.t <= t1)]
            sol = solve_ivp(lambda t, yy: self.rhs(t, yy, F, flow), (t0, t1), y, method="BDF",
                            t_eval=te, jac_sparsity=S, rtol=rtol, atol=atol)
            if not sol.success:
                raise HardStop(f"PADAC_SOLVER_FAILURE: {sol.message}")
            y = sol.y[:, -1]
            ts.extend(sol.t)
            ys.extend(sol.y.T)
        Y = np.array(ys).T
        return self._reduce_solution(np.asarray(ts, float), Y)

    def run_optimized(self, F, q0=None, rtol=1e-5, atol=1e-4, chunk_hours=744, max_step_s=None):
        """Information-preserving orchestration of the SAME MOL equations and SAME hourly forcing.

        Differences from run():
          * flow is evaluated as the original right-continuous hourly schedule inside the RHS;
          * many day/night segments are integrated in one BDF call;
          * the integration is chunked only for memory/checkpoint scale, carrying the exact final state forward;
          * every original hourly timestamp is retained in the returned output.

        This is a numerical-orchestration optimization, not temporal aggregation. It is enabled only after
        regression against run() passes the frozen equivalence gate.
        """
        from scipy.integrate import solve_ivp
        if len(F.t) < 2:
            raise HardStop("PADAC_SOLVER_FAILURE: forcing has fewer than two samples")
        y = self._initial_state(F, q0)
        S = self.sparsity()
        dt = float(np.median(np.diff(F.t)))
        if not np.allclose(np.diff(F.t), dt, rtol=0, atol=max(1e-6, abs(dt)*1e-9)):
            raise HardStop("PADAC_OPT_REQUIRES_REGULAR_TIME_GRID: canonical forcing is not regular")
        n_per = max(2, int(round(float(chunk_hours) * 3600.0 / dt)) + 1)
        frames = []
        a = 0
        while a < len(F.t) - 1:
            b = min(len(F.t) - 1, a + n_per - 1)
            te = F.t[a:b+1]
            kw = {} if max_step_s in (None, 0) else {"max_step": float(max_step_s)}
            sol = solve_ivp(lambda t, yy: self.rhs(t, yy, F, F.flow_at(t)),
                            (float(te[0]), float(te[-1])), y, method="BDF", t_eval=te,
                            jac_sparsity=S, rtol=rtol, atol=atol, **kw)
            if not sol.success:
                raise HardStop(f"PADAC_SOLVER_FAILURE: {sol.message}")
            fr = self._reduce_solution(sol.t, sol.y)
            if frames:
                fr = fr.iloc[1:].copy()  # shared chunk boundary, no information removed
            frames.append(fr)
            y = sol.y[:, -1].copy()
            a = b
        out = pd.concat(frames, ignore_index=True)
        if len(out) != len(F.t) or not np.allclose(out.t_s.to_numpy(float), F.t, rtol=0, atol=1e-6):
            raise HardStop("PADAC_OPT_OUTPUT_GRID_MISMATCH: optimized solver did not preserve every hourly timestamp")
        return out

    def compare_engines(self, F, q0=None, rtol=1e-5, atol=1e-4, chunk_hours=744, max_step_s=None):
        """Regression oracle: legacy segmented vs optimized, on identical forcing and output timestamps."""
        import time
        t0=time.perf_counter(); a=self.run(F,q0=q0,rtol=rtol,atol=atol); legacy_s=time.perf_counter()-t0
        t0=time.perf_counter(); b=self.run_optimized(F,q0=q0,rtol=rtol,atol=atol,chunk_hours=chunk_hours,max_step_s=max_step_s); opt_s=time.perf_counter()-t0
        if len(a)!=len(b) or not np.allclose(a.t_s,b.t_s,rtol=0,atol=1e-6):
            raise HardStop("PADAC_OPT_REGRESSION_GRID_MISMATCH: engines returned different hourly grids")
        cols=[c for c in a.columns if c!='t_s']
        rows=[]
        for c in cols:
            d=a[c].to_numpy(float)-b[c].to_numpy(float)
            rows.append(dict(variable=c,n=len(d),max_abs=float(np.nanmax(np.abs(d))),rmse=float(np.sqrt(np.nanmean(d*d))),mean_abs=float(np.nanmean(np.abs(d))),legacy_seconds=legacy_s,optimized_seconds=opt_s,speedup=(legacy_s/opt_s if opt_s>0 else np.inf)))
        return pd.DataFrame(rows), a, b


# ----------------------------------------------------------------------------- schedules / IRA environmental
def local_time(w, cfg):
    flag = cfg.get("WEATHER_TIMESTAMPS_ARE_LOCAL")
    ts = pd.to_datetime(w["timestamp"], utc=(flag is not True))
    if flag is True:
        return ts.dt.tz_localize(None) if getattr(ts.dt, "tz", None) is not None else ts
    zones = cfg.get("WEATHER_CITY_TIMEZONES") or {}
    if flag is False and zones:
        out = pd.Series(pd.NaT, index=w.index, dtype="datetime64[ns]")
        for c, idx in w.groupby("climate", sort=False).groups.items():
            z = zones.get(str(c))
            if not z:
                raise HardStop(f"TIMEZONE_UNRESOLVED: no IANA timezone for {c}")
            try:
                out.loc[idx] = ts.loc[idx].dt.tz_convert(z).dt.tz_localize(None).values
            except Exception as e:
                raise HardStop(f"TIMEZONE_UNRESOLVED: {c}/{z}: {e}")
        return out
    if flag is False and cfg.get("WEATHER_UTC_OFFSET_H"):
        off = w["climate"].map(cfg["WEATHER_UTC_OFFSET_H"])
        if off.isna().any():
            raise HardStop(f"TIMEZONE_UNRESOLVED: no UTC offset for {sorted(w.climate[off.isna()].unique())}")
        return ts.dt.tz_localize(None) + pd.to_timedelta(off, unit="h")
    raise HardStop("TIMEZONE_UNRESOLVED: canonical weather is UTC; provide WEATHER_CITY_TIMEZONES or explicit offsets.")


def cycle_labels(local_ts, start_h, end_h):
    """Adsorption window [start_h, end_h) (may cross midnight). cycle = date on which adsorption starts;
    the regeneration window is the following [end_h, start_h) period, which belongs to the same cycle."""
    h = local_ts.dt.hour
    ads = ((h >= start_h) | (h < end_h)) if start_h > end_h else ((h >= start_h) & (h < end_h))
    cyc = (local_ts - pd.to_timedelta(start_h, unit="h")).dt.floor("D")
    return ads.values, cyc.values


def ira_loading_trajectory(qstar, dt_h, kern_up, kern_down, mode="kernel_pseudotime", q0=None):
    """Finite-rate loading q(t) toward q*(t) using the MEASURED step-response kernels (t[h], F in [0,1]).
    kernel_pseudotime: memory of the current monotone approach is kept through equivalent elapsed time.
    kernel_memoryless: each hour is a fresh step response (sensitivity only)."""
    n = len(qstar)
    q = np.empty(n)
    q[0] = qstar[0] if q0 is None else q0
    d_prev, q_from = 0, q[0]
    for k in range(n - 1):
        gap = qstar[k] - q[k]
        d = int(np.sign(gap))
        kt, kF = kern_up if d > 0 else kern_down
        if d == 0:
            q[k + 1] = q[k]
            d_prev = 0
            continue
        if mode == "kernel_memoryless":
            q[k + 1] = q[k] + gap * float(np.interp(dt_h, kt, kF))
            continue
        if d != d_prev:
            q_from = q[k]
        span = qstar[k] - q_from
        frac = 0.0 if abs(span) < 1e-15 else np.clip((q[k] - q_from) / span, 0.0, kF[-1] - 1e-12)
        if frac < 0:  # target moved past the start point: restart approach
            q_from, frac = q[k], 0.0
            span = qstar[k] - q_from
        q[k + 1] = q_from + span * pseudotime_step(frac, dt_h, kt, kF)
        d_prev = d
    return q


def _deprecated_hysteresis_states_DO_NOT_USE(rh, rh_low, rh_high, dwell_h):
    """S(t) in {A=0, R=1}: A->R when RH>=rh_high, R->A when RH<=rh_low, each after >= dwell_h in state."""
    s = np.zeros(len(rh), dtype=np.int8)
    st, age = 0, 0
    for k, x in enumerate(rh):
        age += 1
        if st == 0 and x >= rh_high and age >= dwell_h:
            st, age = 1, 0
        elif st == 1 and x <= rh_low and age >= dwell_h:
            st, age = 0, 0
        s[k] = st
    return s


def ira_env_endpoints(q, s):
    dq = np.diff(q)
    naive_all = float(np.sum(np.clip(-dq, 0, None)))
    inR = s[1:] == 1
    naive_inR = float(np.sum(np.clip(-dq[inR], 0, None)))
    seg = 0.0
    nseg = 0
    edges = np.flatnonzero(np.diff(np.r_[0, s, 0]))
    for a, b in zip(edges[::2], edges[1::2]):          # R segment = hours a..b-1; release from entry to exit
        q_entry = q[a - 1] if a > 0 else q[a]
        seg += max(q_entry - q[b - 1], 0.0)
        nseg += 1
    return dict(Y_env_loading_release_segmented=seg, Y_naive_all=naive_all, Y_naive_inR=naive_inR,
                n_R_segments=nseg, double_count_ratio=(naive_inR / seg) if seg > 0 else np.nan)


def padac_params(cfg, sorbent, variant=None):
    """Reactor-side parameters always from CONFIG['PADAC'] (PADAC architecture); sorbent-side passed explicitly."""
    P = cfg["PADAC"]
    v = lambda k: P[k][0]
    form = dict(cfg["PADAC_FORM"])
    r = dict(L=v("L"), D_int=v("D_int"), D_ext=v("D_ext"), e_v=v("e_v"), e_w=v("e_w"), alpha_v=v("alpha_v"),
             eps_v=v("eps_v"), tau_g=v("tau_g"), alpha_w=v("alpha_w"), eps_w=v("eps_w"), rho_v=v("rho_v"), C_v=v("C_v"),
             rho_w=v("rho_w"), C_w=v("C_w"), Q_m3_h=v("Q_m3_h"), sky_coeff=v("sky_coeff"),
             h_w_fitted=v("h_w_fitted"), lambda_gz_fitted=v("lambda_gz_fitted"))
    if variant:
        form["wind_correlation"] = variant["wind_correlation"]
        form["coefficient_mode"] = variant["coefficient_mode"]
        if variant.get("sky_coeff"):
            r["sky_coeff"] = variant["sky_coeff"]
    return dict(reactor=r, sorbent=sorbent, form=form)


def _thermal_job(args):
    """One climate x variant x theta PADAC run (module-level so multiprocessing can pickle it)."""
    P, nz, t, Ta, G, v, flow, out_path, cap, engine, chunk_hours, max_step_s = args
    if os.path.exists(out_path):
        return out_path
    m = PadacModel(P, nz=nz)
    if cap is not None:   # Formulation A: (q_rich mol/kg per time, F_R kernel T grid, dF/dT, bulk density, -dH)
        tq, qr, kT, dF, rho_b, dH = cap
        m.apparent_cap = lambda Ts, tt: rho_b * dH * np.interp(tt, tq, qr) * np.interp(Ts - 273.15, kT, dF, left=0, right=0)
    F = Forcing(t, Ta, G, v, flow)
    if engine == "optimized":
        r = m.run_optimized(F, chunk_hours=chunk_hours, max_step_s=max_step_s)
    elif engine == "legacy_segmented":
        r = m.run(F)
    else:
        raise HardStop(f"UNKNOWN_PADAC_SOLVER_ENGINE: {engine}")
    r.to_parquet(out_path, index=False)
    return out_path


# ----------------------------------------------------------------------------- ImCOF cycles / TPD kernels
def tpd_select(meta, T_ads, RH_ads, cfg):
    """Nearest MEASURED adsorption condition (no interpolation between TPD curves). Returns (curve_id, distance)."""
    d = np.sqrt(((meta["T_ads_C"].to_numpy(float) - T_ads) / cfg["TPD_T_SCALE_C"]) ** 2 +
                ((meta["RH_ads_pct"].to_numpy(float) - RH_ads) / cfg["TPD_RH_SCALE_PCT"]) ** 2)
    i = int(np.argmin(d))
    return meta["curve_id"].iloc[i], float(d[i])


def F_R(kern, cid, T_C):
    """Empirical recovery fraction on the measured TPD ramp; 0 below the first point; held at the ramp-end value
    above the measured range (flagged by callers, never extrapolated upward)."""
    k = kern[cid]
    return np.interp(T_C, k["T"], k["F"], left=0.0, right=k["F"][-1])


def imcof_cycles(local_ts, T, RH, start_h, end_h, mode):
    """Complete daily cycles: adsorption window then regeneration window. Returns DataFrame with
    cycle, T_ads, RH_ads, ads_idx, reg_idx. Incomplete first/last cycles are excluded (identically for all r, pi)."""
    ads, cyc = cycle_labels(pd.Series(pd.to_datetime(local_ts)), start_h, end_h)
    df = pd.DataFrame(dict(cyc=cyc, ads=ads, T=T, RH=RH, i=np.arange(len(T))))
    rows = []
    n_ads = (end_h - start_h) % 24
    for c, g in df.groupby("cyc", sort=True):
        a, r = g[g.ads], g[~g.ads]
        if len(a) != n_ads or len(r) != 24 - n_ads:
            continue
        if mode == "end_of_window":
            Ta, RHa = a["T"].iloc[-1], a["RH"].iloc[-1]
        else:
            Ta, RHa = a["T"].mean(), a["RH"].mean()
        rows.append(dict(cycle=c, T_ads=Ta, RH_ads=RHa, ads_idx=a.i.to_numpy(), reg_idx=r.i.to_numpy()))
    return pd.DataFrame(rows)
