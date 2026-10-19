import csv
import io

from django.http import HttpResponse

from members.domain.repository import MemberRepository


def export_members_csv(members: MemberRepository) -> HttpResponse:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    for member in members.all():
        writer.writerow([member.member_id, member.email])
    return HttpResponse(buffer.getvalue(), content_type="text/csv")
