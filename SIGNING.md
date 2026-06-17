# Jak podepsat ZephyrToSquash.exe

Podepsaná aplikace zobrazí **jméno vydavatele** místo „Unknown Publisher"
a Windows ji bude méně blokovat.

---

## Možnost A – Azure Trusted Signing (~9 USD/měsíc) ✅ Doporučeno

Microsoft přímo vydá certifikát. SmartScreen zná tento certifikát a varuje méně.

### 1. Vytvořte Azure účet
Přejděte na [portal.azure.com](https://portal.azure.com) a přihlaste se (nebo vytvořte účet).

### 2. Zaregistrujte se do Trusted Signing
```
Azure Portal → hledejte "Trusted Signing" → Create account
```
- **Region**: West Europe nebo East US  
- **Tier**: Basic (~9 USD/měsíc)

Vytvořte **Certificate Profile** (typ: PublicTrust nebo PrivateTrust).

### 3. Vytvořte Service Principal (pro GitHub Actions)
```powershell
az ad sp create-for-rbac --name "ZephyrToSquashSigning" --role "Contributor"
```
Uložte si `tenantId`, `clientId`, `clientSecret`.

### 4. Přidejte GitHub Secrets
Jděte na: **GitHub repo → Settings → Secrets → Actions → New repository secret**

| Secret name | Hodnota |
|---|---|
| `AZURE_TENANT_ID` | tenant ID z kroku 3 |
| `AZURE_CLIENT_ID` | client ID z kroku 3 |
| `AZURE_CLIENT_SECRET` | client secret z kroku 3 |
| `AZURE_ENDPOINT` | `https://eus.codesigning.azure.net/` (nebo WEU endpoint) |
| `AZURE_SIGNING_ACCOUNT` | název vašeho Trusted Signing účtu |
| `AZURE_CERT_PROFILE` | název Certificate Profile |

### 5. Spusťte nový release
Pushněte nový tag → GitHub Actions automaticky podepíše `.exe`.

---

## Možnost B – Self-signed certifikát (zdarma, ale omezené)

Odstraní „Unknown Publisher" → zobrazí vaše jméno.  
SmartScreen varování **zůstane**, ale bude méně děsivé.

### 1. Vytvořte certifikát (spusťte na Windows jako Administrátor)
```powershell
# Vytvořit self-signed certifikát
$cert = New-SelfSignedCertificate `
    -Type CodeSigningCert `
    -Subject "CN=Zephyr To Squash Migration Tool, O=CENDIS" `
    -KeyAlgorithm RSA `
    -KeyLength 4096 `
    -HashAlgorithm SHA256 `
    -CertStoreLocation "Cert:\CurrentUser\My" `
    -NotAfter (Get-Date).AddYears(5)

# Exportovat jako PFX
$password = ConvertTo-SecureString -String "VaseHeslo123!" -Force -AsPlainText
Export-PfxCertificate -Cert $cert -FilePath "signing.pfx" -Password $password

# Převést na base64 pro GitHub Secret
[Convert]::ToBase64String([IO.File]::ReadAllBytes("signing.pfx")) | clip
Write-Host "Base64 PFX je ve schránce – vložte jako GitHub Secret SIGNING_CERT_PFX"
```

### 2. Přidejte GitHub Secrets

| Secret name | Hodnota |
|---|---|
| `SIGNING_CERT_PFX` | base64 obsah ze schránky |
| `SIGNING_CERT_PASSWORD` | `VaseHeslo123!` (nebo co jste zadali) |

### 3. Pro firemní počítače: přidejte certifikát jako důvěryhodný
```powershell
# Spustit na každém firemním PC jako admin:
Import-Certificate -FilePath "signing.cer" -CertStoreLocation "Cert:\LocalMachine\TrustedPublisher"
```

---

## Možnost C – SignPath.io (zdarma pro open source)

1. Zaregistrujte se na [signpath.io](https://signpath.io/product/open-source)
2. Požádejte o open-source plán (vyžaduje schválení ~1-2 týdny)
3. Propojte s GitHub repozitářem
4. SignPath automaticky podepisuje při každém releasu

---

## Srovnání výsledků

| | Žádný cert | Self-signed | Azure Trusted | EV certifikát |
|---|---|---|---|---|
| **Publisher** | Unknown | Vaše jméno | Vaše jméno | Vaše jméno |
| **SmartScreen** | ❌ Vždy blokuje | ⚠️ Varuje | ✅ Méně varuje | ✅✅ Nevaruje |
| **Cena** | Zdarma | Zdarma | ~9 USD/měs | 400+ USD/rok |
| **Čas na setup** | - | 10 minut | 1 hodina | 1-2 týdny |
