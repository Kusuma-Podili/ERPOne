# Organization Multi-Tenancy Architecture

## Tenant Modeling
EnterpriseOne supports multi-tenant enterprise operations. An `Organization` represents the primary tenant boundary for all operational domains (branches, departments, teams, employees, CRM records, sales pipelines, financial ledgers, and inventory).

### Multi-Tenancy Principles
1. **Tenant Isolation**:
   - Every business model (Branches, Departments, Teams, and subsequent module models) has an indexed foreign key to `Organization`.
   - `OrganizationContextMiddleware` identifies the active organization for an authenticated user and attaches `request.organization` and `request.organization_member`.
2. **Context Resolution Pipeline**:
   - First checks `request.session['active_organization_id']`.
   - If not set or invalid, falls back to the user's primary active membership (`OrganizationMember.objects.filter(user=request.user, status='ACTIVE')`).
   - Stores the active organization ID in the session for consistent subsequent requests.
   - Users belonging to multiple organizations can switch their active tenant view seamlessly via `/organizations/switch/<org_id>/`.
3. **Tenant Administration & Roles**:
   - `is_org_admin` on `OrganizationMember` grants administrative governance over the tenant's users, branches, departments, and configuration policies.
   - Tenant-level policies (`OrganizationConfiguration`) control self-registration, MFA enforcement, and session timeouts per organization.
