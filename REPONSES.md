# Workshop INFAL105 : Docker et CI/CD GitHub Actions sur Azure

**Étudiant :** Louis BEAUJOIN (GitHub : `louisbeaujoin`)
**Dépôt :** https://github.com/louisbeaujoin/ws-cicd-louis
**Image :** `ghcr.io/louisbeaujoin/ws-cicd-louis`
**Application :** http://9.205.249.132

> Adaptation : comme autorisé, j'ai réutilisé la VM du TP précédent, `tpazure` (groupe `cesizen`, Denmark East, Ubuntu 24.04, Standard_B2s, IP statique) au lieu de créer `vm-cicd-louis`. Le nginx qui occupait le port 80 a été désactivé (`systemctl disable --now nginx`) ; il n'a pas été supprimé.

---

## Exercice 1 : Rôle des fichiers

| Fichier | Rôle |
|---|---|
| `app.py` | Application web Flask : page `/` (message, version, nom du conteneur) et `/health` (JSON `status: ok`, utilisé pour la supervision). |
| `requirements.txt` | Dépendances Python avec versions figées (Flask, Gunicorn), pour un build reproductible. |
| `Dockerfile` | Recette de construction de l'image : image de base, dépendances, code, utilisateur, commande de lancement (Gunicorn). |
| `.dockerignore` | Fichiers exclus du contexte de build (`.git`, secrets, caches) : image plus petite, build plus rapide, pas de fuite de secrets. |
| `.gitignore` | Fichiers exclus du dépôt Git (caches, `venv`, `.env`, clés `*.pem`, `deploy_cicd`), pour ne jamais committer de secret. |
| `.github/workflows/deploy.yml` | Pipeline GitHub Actions : build et publication de l'image dans ghcr.io, puis déploiement SSH sur la VM. |

## Exercice 2 : Conteneurisation

Résultats : `/` affiche le message avec la version `local` ; `/health` renvoie `{"status":"ok","version":"local"}` ; `docker exec webapp whoami` renvoie `appuser` ; l'image pèse environ 49 Mo compressée (200 Mo sur disque).

- **`python:3.12-slim` plutôt que `python:3.12` :** la variante slim est une Debian minimale (environ 120 Mo au lieu d'environ 1 Go). Le téléchargement et le déploiement sont plus rapides, elle consomme moins de disque et réduit la surface d'attaque, puisqu'il y a moins de paquets et donc moins de CVE.
- **Copier `requirements.txt` avant le code :** Docker met chaque couche en cache. Les dépendances changent rarement, le code souvent. Tant que `requirements.txt` ne change pas, la couche `pip install` est réutilisée et seul `COPY app.py` est refait : les builds sont beaucoup plus rapides.
- **`.dockerignore` :** il exclut des fichiers du contexte envoyé au moteur Docker. Les fichiers inutiles ou sensibles (`.git`, `.env`, clés) ne finissent pas dans l'image et le build est plus léger.
- **`-p 8080:5000` :** il publie le port 5000 du conteneur sur le port 8080 de l'hôte (`hôte:conteneur`). Le navigateur appelle `localhost:8080` et Docker redirige vers Gunicorn, qui écoute sur 5000 dans le conteneur.
- **Utilisateur non-root :** si l'application est compromise, l'attaquant n'a pas les droits root dans le conteneur. Une évasion vers l'hôte devient plus difficile, et il ne peut pas modifier le système de fichiers de l'image. C'est le principe du moindre privilège.

## Exercice 3 : Registre

Image `ghcr.io/louisbeaujoin/ws-cicd-louis:1.0` publiée (digest `sha256:3cf21a27…`), package rendu public.

- **Tag ou digest :** un tag (`1.0`, `latest`) est une étiquette lisible mais **mobile** : on peut la réattribuer à une autre image. Un digest (`sha256:…`) est l'empreinte cryptographique du contenu. Il est **immuable** et désigne exactement une image, octet pour octet.
- **Éviter `latest` en production :** on ne sait pas quelle version tourne, `latest` change à chaque publication. Deux serveurs peuvent exécuter des versions différentes, un retour arrière précis est impossible et un redémarrage peut récupérer une version non testée. On préfère un tag immuable (SHA du commit, version sémantique) ou un digest.
- **Risques d'un package public :** tout le monde peut télécharger l'image et l'analyser. Il peut y avoir fuite de code, de secrets oubliés dans une couche, d'informations sur l'architecture, ou de versions vulnérables exploitables. **Alternative :** un package privé, la VM s'authentifiant avec un jeton en lecture seule (`read:packages`), ou un registre privé comme Azure Container Registry (ACR) avec une identité managée.

## Exercice 4 : Hébergement sur la VM

Clé `deploy_cicd` (ed25519) ajoutée à `azureuser`, Docker 29.1.3 installé, `azureuser` ajouté au groupe `docker`. La version 1.0 a été déployée à la main et est accessible sur http://9.205.249.132.

### 4.7 Schéma de l'environnement

```
 POSTE DE TRAVAIL (Windows 11)                 GITHUB
 ┌─────────────────────────────┐   git push    ┌──────────────────────────────────┐
 │ Git, Docker Desktop         │ ────────────► │ Dépôt louisbeaujoin/ws-cicd-louis│
 │ Clé ~/.ssh/deploy_cicd      │   (HTTPS 443) │  └─ Secrets SSH_HOST/USER/KEY    │
 └──────┬──────────────────────┘               │ GitHub Actions (runner Ubuntu)   │
        │ docker push 1.0 (HTTPS 443)          │  job 1 build-and-push ───┐       │
        ▼                                      │  job 2 deploy (needs)    │push   │
 ┌──────────────────────────────┐   ◄──────────┼──────────────────────────┘       │
 │ REGISTRE ghcr.io (public)    │              └───────────┬──────────────────────┘
 │ ws-cicd-louis:1.0, :<sha>    │                          │ SSH (TCP 22)
 └──────────────┬───────────────┘                          │ + test HTTP /health
                │ docker pull (HTTPS 443, sortant)         │
 AZURE ─ abonnement Azure for Students ─ région Denmark East
 ┌──────────────┼──────────────────────────────────────────┼─────────────────────┐
 │ Groupe de ressources cesizen                            │                     │
 │  IP publique tpazure-ip 9.205.249.132 (statique)        │                     │
 │  NSG tpazure-nsg : Allow 22/TCP (prio 300)  ◄───────────┘                     │
 │                    Allow 80/TCP (prio 310)  ◄──── Utilisateurs (HTTP 80)      │
 │  ┌ VNet vnet-denmarkeast-1 ─ Subnet snet-denmarkeast-1 ─────────────────────┐ │
 │  │  NIC tpazure630 (172.16.0.4)                                             │ │
 │  │  ┌ VM tpazure (Ubuntu 24.04, B2s, utilisateur azureuser) ──────────────┐ │ │
 │  │  │  Docker Engine                                                      │ │ │
 │  │  │   └ conteneur "webapp" (appuser) : port hôte 80 ──► port 5000       │ │ │
 │  │  │      Gunicorn + Flask, --restart unless-stopped                     │ │ │
 │  │  └─────────────────────────────────────────────────────────────────────┘ │ │
 │  └──────────────────────────────────────────────────────────────────────────┘ │
 │  Serveur PostgreSQL flexible cezidb (TP précédent, bonus)                     │
 └───────────────────────────────────────────────────────────────────────────────┘
```

### 4.8 Questions

- **Pourquoi le port 22 doit rester ouvert :** le job `deploy` s'exécute sur un runner hébergé par GitHub, sur Internet, avec une IP variable dans les larges plages d'Azure. Il se connecte en SSH pour faire `docker pull` et `docker run`. Si on ferme le port 22, ou si on le restreint à notre IP, le pipeline ne peut plus joindre la VM.
- **Risque :** le port 22 est exposé à tout Internet : scans, attaques par force brute, exploitation d'une faille d'OpenSSH. Si la clé privée fuit, par exemple depuis les secrets, n'importe qui prend la main sur la VM. **Mesures :** clé uniquement (mot de passe désactivé), fail2ban, Azure Bastion ou un runner auto-hébergé dans le VNet, restriction du NSG aux plages IP de GitHub, ou un modèle *pull* où la VM récupère elle-même les mises à jour (Watchtower, par exemple).
- **Groupe `docker` sensible :** l'accès au socket Docker équivaut à **root sur l'hôte**. Avec `docker run -v /:/host --privileged …`, on peut lire et modifier tout le système de fichiers de la VM sans `sudo`. Compromettre `azureuser` ou la clé de déploiement donne donc un contrôle total de la machine.

## Exercice 5 : Pipeline GitHub Actions

Workflow complété (TODO 1 à 7) : déclenchement sur `push` vers `main`, permissions `contents: read` / `packages: write`, connexion avec `docker/login-action@v3` et `GITHUB_TOKEN`, build avec `docker/build-push-action@v6` (tags `:<sha>` et `:latest`, `APP_VERSION=<sha>`), `needs: build-and-push`, préparation SSH, puis déploiement (`set -e`, `docker pull`, `docker rm -f`, `docker run`).

Résultat : le premier lancement a échoué avec `Load key … error in libcrypto`. Le secret `SSH_KEY` contenait des fins de ligne Windows (CRLF). Après correction, le site affichait la version `5df8c04` = `git rev-parse --short HEAD`. ✅

- **SHA du commit comme tag :** le tag est unique et immuable. Chaque image est reliée exactement au code qui l'a produite (traçabilité, audit). On sait toujours quelle version tourne, et revenir en arrière consiste à redéployer un tag précédent. Deux builds ne s'écrasent jamais.
- **`needs` :** il crée une dépendance. `deploy` ne démarre qu'**après la réussite** de `build-and-push`. Si le premier job échoue, `deploy` est **ignoré** (skipped) : on ne déploie jamais une image qui n'a pas été construite ou publiée, et la version en production reste en place.
- **Relire un secret :** non. Une fois enregistrée, la valeur n'est plus visible, ni dans l'interface ni par l'API : on peut seulement la remplacer ou la supprimer. Dans les journaux, GitHub la **masque** automatiquement par `***`, comme on le voit avec `ssh … "***@***"`. Attention : une valeur transformée (encodée en base64, découpée) ne serait pas masquée.
- **`GITHUB_TOKEN` plutôt que le jeton personnel :** il est généré automatiquement à chaque exécution et expire à la fin du job. Ses droits se limitent au dépôt et à ce que déclare `permissions:`. Il n'y a rien à stocker, renouveler ou révoquer, et il ne donne pas accès à tous vos dépôts, contrairement au jeton classic, qui inclut `repo`. C'est le principe du moindre privilège.
- **`ssh-keyscan` :** il récupère la clé publique de l'hôte SSH et l'ajoute à `known_hosts`, pour que la connexion ne bloque pas sur la question « Are you sure you want to continue connecting? ». **Risque :** il fait confiance à la clé reçue au premier contact (TOFU), sans la vérifier. Un attaquant en position d'interception (*man-in-the-middle*, DNS ou IP détournés) pourrait présenter sa propre clé : le pipeline lui enverrait les commandes de déploiement. **Mieux :** stocker l'empreinte connue de la VM dans un secret `SSH_KNOWN_HOSTS`.

## Exercice 6 : Modifier, déployer, revenir en arrière

| Étape | Commit | Résultat |
|---|---|---|
| Message personnalisé | `e61316c` | Pipeline vert, nouvelle version visible **36 s** après le `git push` |
| Version défectueuse (parenthèse supprimée) | `e7fc548` | **Pipeline vert**, alors que le site ne répond plus (connexion refusée) |
| `git revert HEAD` | `fe1d7f7` | Service rétabli en **39 s** |
| Ajout de l'étape « Test de santé » | `e04d95b` | Pipeline vert |
| Version défectueuse à nouveau | `afe19be` | **Pipeline rouge** : « L'application ne répond pas sur /health » |
| `git revert HEAD` | `4dbd87d` | Pipeline vert, site rétabli |

**6.3, ce que l'on observe avec la version défectueuse :**
- **Pipeline :** vert. Le build ne fait qu'empaqueter le code sans l'exécuter, et `docker run -d` réussit dès que le conteneur démarre.
- **Utilisateur :** le site est indisponible (erreur de connexion, HTTP 000).
- **`docker ps -a` sur la VM :** `webapp … Restarting (3) 3 seconds ago`. Le conteneur redémarre en boucle à cause de `--restart unless-stopped`. `docker logs` affiche `SyntaxError: '(' was never closed` puis `Worker failed to boot`.

**6.5, étape ajoutée au workflow :**

```yaml
- name: Test de santé
  run: |
    for i in $(seq 1 10); do
      if curl -fsS --max-time 5 "http://${{ secrets.SSH_HOST }}/health" | grep -q '"status":"ok"'; then
        echo "Application en bonne santé"; exit 0
      fi
      echo "Tentative $i/10 : pas de réponse, nouvel essai dans 5 s"; sleep 5
    done
    echo "::error::L'application ne répond pas sur /health"; exit 1
```

**6.6 Questions :**

- **`git revert` plutôt que `reset --hard` + `push --force` :** `revert` crée un **nouveau commit** qui annule le précédent. L'historique est conservé, l'opération est traçable (qui a annulé quoi et quand), auditable et elle-même réversible, et elle redéclenche normalement le pipeline. `reset` + `push --force` **réécrit l'historique partagé** : les commits disparaissent, les clones des collègues divergent, du travail peut être perdu, et la trace de l'incident est effacée. Sur `main`, le force-push est d'ailleurs souvent interdit par une protection de branche.
- **Indisponibilité pendant un déploiement :** oui, une courte coupure. Entre `docker rm -f webapp` et le démarrage de Gunicorn dans le nouveau conteneur, plus rien n'écoute sur le port 80 (quelques secondes). **Pour l'éviter :**
  - déploiement *blue/green* : lancer la nouvelle version sur un autre port, vérifier `/health`, basculer un reverse proxy (nginx, Traefik), puis arrêter l'ancienne ;
  - *rolling update* sur plusieurs instances derrière un équilibreur de charge ;
  - utiliser un service managé : *deployment slots* d'App Service, révisions de Container Apps.
- **Anciennes images sur la VM :** elles **restent sur le disque**. On en voit 8 de 200 Mo chacune (`1.0` et un tag par SHA), et le disque finira par se remplir. **Libérer de l'espace :** `docker image prune -a` (images non utilisées par un conteneur), ou `docker system prune -a` (images, conteneurs arrêtés, réseaux, cache). On peut ajouter `docker image prune -af --filter "until=168h"` à la fin du déploiement, en gardant les dernières versions pour pouvoir revenir en arrière rapidement.

## Exercice 7 : Analyse et stratégie d'hébergement

### 7.1 Tableau comparatif

| Critère | VM + Docker + CI/CD SSH | Azure App Service (conteneur) | Azure Container Apps |
|---|---|---|---|
| **Mises à jour du système** | À notre charge : patchs Ubuntu, Docker, OpenSSH, redémarrages (`unattended-upgrades`). | Gérées par Azure (OS, runtime de la plateforme) ; on ne maintient que l'image. | Gérées par Azure (plateforme Kubernetes sous-jacente invisible) ; on ne maintient que l'image. |
| **Mise à l'échelle** | Manuelle : redimensionner la VM (vertical, avec coupure) ou créer d'autres VM + équilibreur (VM Scale Sets). Pas d'autoscaling simple. | Verticale (changer de plan) et horizontale (nombre d'instances) ; autoscale selon des règles sur les plans Standard et supérieurs. | Automatique et fine (KEDA) : selon les requêtes HTTP, la CPU, les files de messages ; **scale-to-zero** possible. |
| **Effort de mise en place du déploiement** | Élevé : VM, NSG, Docker, clés SSH, secrets, script de déploiement, health check, nettoyage, *zero downtime* à construire soi-même. | Faible : pointer vers l'image ; webhook ou action `azure/webapps-deploy` ; *deployment slots* intégrés. | Faible à moyen : `az containerapp up` ou action dédiée ; révisions et répartition du trafic intégrées. |
| **Surface d'attaque** | Large : OS complet, port 22 ouvert sur Internet, socket Docker, clé SSH privée dans GitHub. | Réduite : pas de SSH public, HTTPS et certificats gérés, OS durci par Microsoft. | Réduite : pas d'accès à l'hôte, ingress HTTPS géré, intégration VNet et identité managée. |
| **Modèle de coût** | Paiement à l'heure de la VM, **même inactive** (+ disque + IP publique). Prévisible ; on paie la capacité. | Paiement du **plan App Service** (instances réservées en continu), quel que soit le trafic. Niveau Free/B1 pour les tests. | Paiement **à la consommation** (vCPU·s, Go·s, requêtes) avec quota gratuit mensuel ; quasi nul à zéro réplica. |
| **Portabilité (verrouillage)** | Forte portabilité : Docker standard, déplaçable chez n'importe quel hébergeur ou VM. Verrouillage faible. | Image Docker portable, mais configuration, slots et paramètres propres à Azure. Verrouillage moyen. | Image portable, Dapr et KEDA sont open source, mais la configuration est propre à Azure (≈ Cloud Run d'AWS/GCP). Verrouillage moyen. |

**Conclusion :** pour une petite application web sans état comme celle-ci, **Azure Container Apps** (ou App Service) est plus adapté. Le service est moins cher à faible trafic grâce au *scale-to-zero*, il n'y a pas de système à maintenir, pas de port 22 exposé, et le déploiement se fait sans coupure. La solution VM + Docker reste pertinente pour l'apprentissage, pour un besoin de contrôle total (logiciel particulier, accès au système), pour une charge constante, ou pour minimiser le verrouillage chez un fournisseur.

### 7.2 Risques de sécurité et mesures

| # | Risque | Mesure |
|---|---|---|
| 1 | **Port SSH 22 ouvert à tout Internet** (force brute, faille d'OpenSSH) | Restreindre le NSG (plages IP de GitHub Actions), Azure Bastion, fail2ban, ou runner auto-hébergé dans le VNet / modèle *pull* sans port entrant. |
| 2 | **Clé privée SSH stockée dans GitHub et sans phrase secrète** ; sa fuite donne accès à la VM | Secret d'**environnement** protégé (règles de validation), rotation régulière, clé dédiée limitée par `command=` dans `authorized_keys`, ou authentification OIDC Azure (fédération d'identité) sans secret longue durée. |
| 3 | **Groupe `docker` = root** : la compromission du compte de déploiement donne le contrôle total de la VM | Docker *rootless*, compte de déploiement restreint à un script `sudo` précis, VM dédiée sans autre service ni donnée. |
| 4 | **Jeton personnel (PAT classic) trop large** : `write:packages` impose `repo`, accès complet aux dépôts ; collé en clair pendant le TP | Expiration courte (7 jours) et **révocation** dès la fin ; utiliser `GITHUB_TOKEN` dans la CI ; ne jamais coller un jeton dans un chat ou un fichier. |
| 5 | **Package public** : l'image peut être analysée (code, éventuels secrets dans une couche) | Package privé + jeton `read:packages` sur la VM, ou ACR avec identité managée ; ne jamais mettre de secret dans l'image (utiliser des variables d'environnement à l'exécution). |
| 6 | **`ssh-keyscan` sans vérification (TOFU)** : attaque de l'homme du milieu possible | Stocker l'empreinte de l'hôte dans un secret `SSH_KNOWN_HOSTS`. |
| 7 | **Site en HTTP seulement** (trafic en clair) | HTTPS via un reverse proxy (Caddy ou nginx + Let's Encrypt) ou service managé avec certificat. |
| 8 | **Image et dépendances vulnérables**, actions tierces non figées (`@v3`) | Scan d'image (Trivy, Dependabot), mises à jour régulières de la base `slim`, actions figées par SHA de commit. |
| 9 | **Pas de mises à jour automatiques de l'OS** | `unattended-upgrades`, Azure Update Manager. |

### 7.3 Coût

VM utilisée : **Standard_B2s** (2 vCPU, 4 Go), Linux, Denmark East, paiement à l'utilisation 730 h/mois. Ordres de grandeur, à confirmer dans le calculateur (https://azure.microsoft.com/fr-fr/pricing/calculator/) :

| Élément | Estimation mensuelle |
|---|---|
| VM B2s (≈ 0,045 €/h × 730 h) | ≈ 33 € |
| Disque OS SSD Premium P4 (30 Go) | ≈ 5 € |
| IP publique statique standard | ≈ 3,5 € |
| **Total** | **≈ 40 € / mois** |

Avec une **Standard_B1s** (taille prévue par le TP), le coût serait d'environ 8 à 10 € par mois pour la VM, soit environ 17 € au total.

**Suivi du crédit Azure for Students :** dans le portail, *Abonnements* > *Azure for Students* > *Vue d'ensemble*, ou *Gestion des coûts + facturation* > *Crédits Azure*, ou encore https://www.microsoftazuresponsorships.com/balance. On peut aussi passer par le *hub Éducation* (https://portal.azure.com/#view/Microsoft_Azure_Education/EducationMenuBlade/~/overview). Créer un **budget avec alerte** dans *Gestion des coûts* est recommandé.

### 7.5 Nettoyage (adapté à la réutilisation de `tpazure`)

On **ne supprime pas** le groupe `cesizen`, qui contient la VM et `cezidb` du TP précédent. Le nettoyage du workshop consiste à :

1. Arrêter et supprimer le conteneur et les images sur la VM : `docker rm -f webapp && docker image prune -af`.
2. Retirer la clé `deploy-cicd-louis` de `~azureuser/.ssh/authorized_keys`.
3. Si besoin, réactiver le site d'origine : `sudo systemctl enable --now nginx`.
4. Révoquer le jeton `ghcr-workshop` (GitHub > Settings > Developer settings > Tokens (classic)).
5. Supprimer les secrets `SSH_HOST`, `SSH_USER` et `SSH_KEY` du dépôt, puis la clé locale `~/.ssh/deploy_cicd` (et `.pub`).
6. Supprimer, si besoin, le package `ws-cicd-louis` (Package settings > Delete).
7. Vérifier le crédit restant.

Le groupe `rg-ws-cicd-louis`, créé par erreur puis abandonné, a déjà été supprimé (il était vide).
