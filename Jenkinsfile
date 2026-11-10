// Jenkinsfile - Resource Link Hub (UTS Cloud Computing - Studi Kasus No. 9)
// Disesuaikan dengan setup lab: Jenkins berjalan sebagai kontainer (jenkins-server)
// di Docker Desktop Windows, memakai /var/run/docker.sock milik host.

pipeline {
    agent any

    triggers {
        githubPush()   // dipicu otomatis oleh GitHub Webhook setiap git push ke main
    }

    environment {
        COMPOSE_PROJECT_NAME = 'link-hub'
        FRONTEND_CONTAINER   = 'link-hub-frontend'
    }

    stages {
        stage('1. Checkout') {
            steps {
                checkout scm
                sh 'git log -1 --oneline'
            }
        }

        stage('2. Syntax Check') {
            steps {
                sh 'python3 --version'
                sh 'python3 -m py_compile backend/app.py && echo "Syntax backend/app.py OK"'
                sh 'docker compose config -q && echo "docker-compose.yml valid"'
            }
        }

        stage('3. Build Image') {
            steps {
                sh 'docker compose build'
                sh 'docker image ls link-hub-backend'
            }
        }

        stage('4. Automated Deployment') {
            steps {
                script {
                    // Jenkins ada di dalam kontainer, jadi path workspace (/var/jenkins_home/...)
                    // tidak dikenal Docker host. Cari sumber mount /var/jenkins_home milik
                    // kontainer Jenkins, lalu susun path host untuk Bind Mount frontend.
                    def jh = env.JENKINS_HOME ?: '/var/jenkins_home'
                    def src = sh(
                        script: "docker inspect \"\$(hostname)\" --format '{{range .Mounts}}{{if eq .Destination \"${jh}\"}}{{.Source}}{{end}}{{end}}' 2>/dev/null || true",
                        returnStdout: true
                    ).trim()
                    env.HOST_PROJECT_DIR = (src && env.WORKSPACE.startsWith(jh)) ?
                        (src + env.WORKSPACE.substring(jh.length())) : env.WORKSPACE
                    echo "HOST_PROJECT_DIR untuk Bind Mount: ${env.HOST_PROJECT_DIR}"
                }
                sh 'docker compose up -d --remove-orphans --force-recreate'
                sh 'docker compose ps'
            }
        }

        stage('5. Health Check') {
            steps {
                sh '''
                    # Cek API lewat Nginx -> service "backend" (sekaligus membuktikan DNS Docker di app-net)
                    for i in $(seq 1 10); do
                        if docker exec ${FRONTEND_CONTAINER} wget -qO- http://localhost/api/health; then
                            echo ""
                            echo "Health check API OK (percobaan ke-$i)"
                            break
                        fi
                        if [ "$i" -eq 10 ]; then
                            echo "Health check GAGAL"
                            docker compose logs --tail 30
                            exit 1
                        fi
                        echo "Belum siap, coba lagi ($i/10)..."
                        sleep 3
                    done

                    # Cek halaman frontend dari Bind Mount benar-benar tersaji
                    docker exec ${FRONTEND_CONTAINER} wget -qO- http://localhost/ | grep -q "Resource Link Hub" \
                        && echo "Frontend (Bind Mount) OK" \
                        || { echo "Frontend tidak tersaji dari Bind Mount"; exit 1; }

                    docker exec ${FRONTEND_CONTAINER} wget -qO- http://localhost/api/links
                    echo ""
                '''
            }
        }
    }

    post {
        success { echo 'DEPLOY SUKSES - buka http://localhost:8081' }
        failure { echo 'PIPELINE GAGAL - cek log stage yang merah' }
    }
}
