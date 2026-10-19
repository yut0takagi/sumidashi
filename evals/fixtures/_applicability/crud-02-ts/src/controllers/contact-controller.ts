import { Body, Controller, Delete, Get, Param, ParseIntPipe, Patch, Post } from "@nestjs/common";
import { ContactService } from "../services/contact-service";

@Controller("contacts")
export class ContactController {
  constructor(private readonly contacts: ContactService) {}

  @Get()
  findAll() {
    return this.contacts.findAll();
  }

  @Get(":id")
  findOne(@Param("id", ParseIntPipe) id: number) {
    return this.contacts.findOne(id);
  }

  @Post()
  create(@Body() body: { name: string; email: string }) {
    return this.contacts.create(body.name, body.email);
  }

  @Patch(":id")
  update(@Param("id", ParseIntPipe) id: number, @Body() body: { name?: string; email?: string }) {
    return this.contacts.update(id, body);
  }

  @Delete(":id")
  remove(@Param("id", ParseIntPipe) id: number) {
    return this.contacts.remove(id);
  }
}
